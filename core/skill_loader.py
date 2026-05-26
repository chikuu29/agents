# core/skill_loader.py

import re
from pathlib import Path
from dataclasses import dataclass,field
from typing import Dict,List,Optional,Any
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


@dataclass
class SkillManifest:
    name: str
    description: str
    triggers: list[str]
    mcp_servers: list[str]
    md_path: Path
    full_content: str = field(repr=False)


def _parse_frontmatter(text: str) -> dict:
    """Parse YAML-Like Frontmatter between --- fences."""
    # Find frontmatter between ---
    # regex to find YAML frontmatter between --- fences at the start of the file
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL) # TODO: use regex to find YAML frontmatter between --- fences at the start of the file
    if not match:
        # Try without starting newline just in case
        match = re.match(r"^---\s*(.*?)\n---\s*\n", text, re.DOTALL) # TODO: use regex to find YAML frontmatter between --- fences at the start of the file
    
    if not match:
        return {}
    
    yaml_content = match.group(1)
    try:
        import yaml
        return yaml.safe_load(yaml_content) or {}
    except ImportError:
        # Fallback basic YAML parser if yaml library is not available
        data = {}
        current_key = None
        for line in yaml_content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('- '):
                if current_key and isinstance(data.get(current_key), list):
                    data[current_key].append(line[2:].strip().strip('"').strip("'"))
                continue
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip()
                if val == '':
                    data[key] = []
                    current_key = key
                else:
                    data[key] = val.strip('"').strip("'")
                    current_key = key
        return data


def load_skills(skill_dir: str = "skills") -> List[SkillManifest]:
    skills = []
    for md_file in Path(skill_dir).rglob("SKILL.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
            metadata = _parse_frontmatter(text)
            print(f"metadata: {metadata}")
            if not metadata:
                logger.warning(f"Could not parse frontmatter in {md_file}")
                continue
            
            # Extract fields with safe fallbacks
            name = metadata.get("name", md_file.parent.name)
            description = metadata.get("description", "")
            
            triggers = metadata.get("triggers", [])
            if isinstance(triggers, str):
                triggers = [triggers]
                
            mcp_servers = metadata.get("mcp_servers", [])
            if isinstance(mcp_servers, str):
                mcp_servers = [mcp_servers]

            # Create manifest
            skills.append(SkillManifest(
                name=name,
                description=description,
                triggers=list(triggers),
                mcp_servers=list(mcp_servers),
                md_path=md_file,
                full_content=text
            ))
        except Exception as e:
            logger.error(f"Error loading skill from {md_file}: {e}")
            
    return skills


if __name__ == "__main__":
    import pprint
    pprint.pprint(load_skills("skills"))