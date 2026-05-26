# core/observability.py
"""
OpenTelemetry observability setup.

Provides distributed tracing and metrics for the agent system.
Supports two export modes:
- Console (default): Prints spans and metrics to stdout
- OTLP: Exports to a collector (Jaeger, Grafana Tempo, etc.)

Metrics tracked:
- agent.requests.total       — Total requests processed
- agent.llm.latency_ms       — LLM call duration histogram
- agent.llm.tokens.input     — Input token counter
- agent.llm.tokens.output    — Output token counter
- agent.tools.calls          — Tool call counter by tool name
- agent.errors.total         — Error counter by type
- agent.skill.routed         — Skill routing counter by skill name
"""

import structlog
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    ConsoleMetricExporter,
)
from opentelemetry.sdk.resources import Resource

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level meter and counters (initialized by setup_observability)
# ---------------------------------------------------------------------------

_meter: metrics.Meter | None = None

# Counters and histograms (initialized in setup)
request_counter: metrics.Counter | None = None
llm_latency_histogram: metrics.Histogram | None = None
llm_input_tokens_counter: metrics.Counter | None = None
llm_output_tokens_counter: metrics.Counter | None = None
tool_call_counter: metrics.Counter | None = None
error_counter: metrics.Counter | None = None
skill_route_counter: metrics.Counter | None = None


def setup_observability(settings) -> None:
    """
    Initialize OpenTelemetry tracing and metrics.

    Args:
        settings: Settings object with otlp_endpoint, service_name attributes.
    """
    global _meter
    global request_counter, llm_latency_histogram
    global llm_input_tokens_counter, llm_output_tokens_counter
    global tool_call_counter, error_counter, skill_route_counter

    resource = Resource.create({
        "service.name": settings.service_name,
        "service.version": "0.1.0",
    })

    # --- Tracing ---
    tracer_provider = TracerProvider(resource=resource)

    if settings.otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
            tracer_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
            logger.info(
                "observability.otlp_trace_enabled",
                endpoint=settings.otlp_endpoint,
            )
        except ImportError:
            logger.warning("observability.otlp_import_failed", msg="Falling back to console")
            tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        # Console exporter for development
        tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(tracer_provider)

    # --- Metrics ---
    if settings.otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=settings.otlp_endpoint),
                export_interval_millis=30000,
            )
        except ImportError:
            metric_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=60000,
            )
    else:
        metric_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=60000,
        )

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(meter_provider)

    # --- Create Instruments ---
    _meter = metrics.get_meter("agent-system", "0.1.0")

    request_counter = _meter.create_counter(
        name="agent.requests.total",
        description="Total agent requests processed",
        unit="1",
    )

    llm_latency_histogram = _meter.create_histogram(
        name="agent.llm.latency_ms",
        description="LLM call latency in milliseconds",
        unit="ms",
    )

    llm_input_tokens_counter = _meter.create_counter(
        name="agent.llm.tokens.input",
        description="Total LLM input tokens consumed",
        unit="tokens",
    )

    llm_output_tokens_counter = _meter.create_counter(
        name="agent.llm.tokens.output",
        description="Total LLM output tokens consumed",
        unit="tokens",
    )

    tool_call_counter = _meter.create_counter(
        name="agent.tools.calls",
        description="Total MCP tool calls by tool name",
        unit="1",
    )

    error_counter = _meter.create_counter(
        name="agent.errors.total",
        description="Total errors by type",
        unit="1",
    )

    skill_route_counter = _meter.create_counter(
        name="agent.skill.routed",
        description="Skill routing count by skill name",
        unit="1",
    )

    logger.info(
        "observability.configured",
        service_name=settings.service_name,
        otlp_enabled=bool(settings.otlp_endpoint),
    )


def record_llm_call(
    provider: str,
    model: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Record metrics for a single LLM call."""
    attributes = {"provider": provider, "model": model}

    if llm_latency_histogram:
        llm_latency_histogram.record(latency_ms, attributes)
    if llm_input_tokens_counter:
        llm_input_tokens_counter.add(input_tokens, attributes)
    if llm_output_tokens_counter:
        llm_output_tokens_counter.add(output_tokens, attributes)


def record_tool_call(tool_name: str) -> None:
    """Record a tool call metric."""
    if tool_call_counter:
        tool_call_counter.add(1, {"tool": tool_name})


def record_error(error_type: str, skill: str = "") -> None:
    """Record an error metric."""
    if error_counter:
        error_counter.add(1, {"type": error_type, "skill": skill})


def record_request(skill: str) -> None:
    """Record a request and skill routing metric."""
    if request_counter:
        request_counter.add(1, {"skill": skill})
    if skill_route_counter:
        skill_route_counter.add(1, {"skill": skill})
