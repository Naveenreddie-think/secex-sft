"""
Fetches security advisories from the GitHub Advisory Database (GHSA) via GraphQL.
Run as: python -m app.data_pipeline.fetch_ghsa --limit 50
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

from app.config import settings

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($first: Int!, $after: String) {
  securityAdvisories(first: $first, after: $after, orderBy: {field: PUBLISHED_AT, direction: DESC}) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ghsaId
      summary
      description
      severity
      publishedAt
      identifiers {
        type
        value
      }
      cvss {
        score
        vectorString
      }
      cwes(first: 5) {
        nodes {
          cweId
          name
        }
      }
      vulnerabilities(first: 10) {
        nodes {
          package {
            ecosystem
            name
          }
          vulnerableVersionRange
        }
      }
      references {
        url
      }
    }
  }
}
"""

def fetch_page(after_cursor: str | None, page_size: int = 25) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Content-Type": "application/json",
    }
    variables = {"first": page_size, "after": after_cursor}
    response = requests.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": variables},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]["securityAdvisories"]


def fetch_advisories(limit: int) -> list[dict]:
    collected: list[dict] = []
    after_cursor = None
    page_size = min(25, limit)

    while len(collected) < limit:
        remaining = limit - len(collected)
        current_page_size = min(page_size, remaining)

        result = fetch_page(after_cursor, current_page_size)
        nodes = result["nodes"]
        collected.extend(nodes)

        print(f"Fetched {len(collected)}/{limit} advisories...")

        if not result["pageInfo"]["hasNextPage"]:
            print("Reached end of available advisories.")
            break

        after_cursor = result["pageInfo"]["endCursor"]
        time.sleep(0.5)  # be polite to the API

    return collected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", type=str, default="data/raw/ghsa_advisories.json")
    args = parser.parse_args()

    try:
        advisories = fetch_advisories(args.limit)
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        print(f"Response body: {e.response.text}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(advisories, indent=2), encoding="utf-8")

    print(f"Saved {len(advisories)} advisories to {out_path}")


if __name__ == "__main__":
    main()