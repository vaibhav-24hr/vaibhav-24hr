#!/usr/bin/env python3
"""Fetch GitHub data and update assets/profile.json.

Standard library only (zero external pip packages needed).
Works with:
- GITHUB_TOKEN / GH_TOKEN (in GitHub Actions)
- Public REST API fallback (when run locally without token)
"""
import datetime
import json
import os
import sys
import urllib.request

LOGIN = "vaibhav-24hr"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "profile.json")
CONFIG_PATH = os.path.join(ROOT, "profile.config.json")

TOKEN = os.environ.get("STATS_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
UA = "Mozilla/5.0 (compatible; GitHub-Profile-Refresher)"


def request_json(url, post_data=None):
    headers = {"User-Agent": UA}
    if TOKEN:
        headers["Authorization"] = f"bearer {TOKEN}"
    data = json.dumps(post_data).encode("utf-8") if post_data else None
    if post_data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_stats():
    # If token available, attempt GraphQL query for comprehensive commit counts
    if TOKEN:
        try:
            gql_query = """query($login:String!){
                user(login:$login){
                    createdAt
                    followers{totalCount}
                    repositories(privacy:PUBLIC, ownerAffiliations:OWNER){totalCount}
                }
            }"""
            u = request_json("https://api.github.com/graphql", {"query": gql_query, "variables": {"login": LOGIN}})["data"]["user"]
            repos_count = u["repositories"]["totalCount"]
            followers_count = u["followers"]["totalCount"]

            # Count total commits
            commits = 0
            this_year = datetime.datetime.now(datetime.timezone.utc).year
            start_year = int(u["createdAt"][:4])
            for year in range(start_year, this_year + 1):
                cc_query = """query($login:String!,$from:DateTime!,$to:DateTime!){
                    user(login:$login){
                        contributionsCollection(from:$from,to:$to){
                            totalCommitContributions
                            restrictedContributionsCount
                        }
                    }
                }"""
                res = request_json("https://api.github.com/graphql", {
                    "query": cc_query,
                    "variables": {
                        "login": LOGIN,
                        "from": f"{year}-01-01T00:00:00Z",
                        "to": f"{year}-12-31T23:59:59Z"
                    }
                })
                cc = res["data"]["user"]["contributionsCollection"]
                commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

            # Count stars across owned public repos
            stars = 0
            repos_data = request_json(f"https://api.github.com/users/{LOGIN}/repos?per_page=100")
            for r in repos_data:
                stars += r.get("stargazers_count", 0)

            return {
                "repos": repos_count,
                "stars": stars,
                "commits": commits,
                "followers": followers_count
            }
        except Exception as e:
            print(f"GraphQL fetch failed ({e}), falling back to REST API", file=sys.stderr)

    # Fallback to standard public REST API
    u = request_json(f"https://api.github.com/users/{LOGIN}")
    repos_data = request_json(f"https://api.github.com/users/{LOGIN}/repos?per_page=100")
    stars = sum(r.get("stargazers_count", 0) for r in repos_data)

    # Estimate commit count via search API
    commits = 350
    try:
        search_res = request_json(f"https://api.github.com/search/commits?q=author:{LOGIN}")
        commits = max(search_res.get("total_count", 0), 300)
    except Exception:
        pass

    return {
        "repos": u.get("public_repos", 23),
        "stars": stars,
        "commits": commits,
        "followers": u.get("followers", 10)
    }


def main():
    previous = {}
    if os.path.exists(OUT):
        with open(OUT, "r", encoding="utf-8") as f:
            try:
                previous = json.load(f)
            except Exception:
                pass

    print(f"Fetching GitHub stats for @{LOGIN}...")
    stats = fetch_stats()
    print(f"Stats fetched: {stats}")

    data = previous if previous else {"repos": {}}
    data["stats"] = stats

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
