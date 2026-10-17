#!/usr/bin/env python3
"""Single entry point for every generated catalogue, API and documentation artifact."""
from build_skills_index import build as index
from build_skill_docs import build as docs
from build_api import build as api
from validate_site import validate
if __name__=='__main__':
    index();docs();api();validate()
