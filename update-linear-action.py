import argparse
import re
import sys
from functools import wraps

import requests

# Parse arguments
parser = argparse.ArgumentParser(prog="top", description="Show top lines from each file")
parser.add_argument("-k", "--token", help="linear API token", required=True)
parser.add_argument("-b", "--branch", help="PR branch name")
parser.add_argument("-t", "--title", help="PR title")
parser.add_argument("-d", "--description", help="PR description text")
parser.add_argument("-c", "--comment", help="Linear comment text to add")
parser.add_argument("-l", "--label", help="Linear label to add")
args = parser.parse_args()._get_kwargs()

LINEAR_TOKEN = dict(args).get("token")

args = dict(args[1:])

url = "https://api.linear.app/graphql"
headers = {"Authorization": LINEAR_TOKEN, "Content-Type": "application/json"}


def get_issue(team_key, issue_number):
    query = """
    query Issues($teamKey: String!, $issueNumber: Float) { 
        issues(filter: {team: {key: {eq: $teamKey}}, number: {eq: $issueNumber}}) {
            nodes {
                id,
                branchName,
                parent {
                    id
                },
                team {
                    id
                },
                labels {
                    nodes {
                        id
                    }
                }
            }
        }
    }
    """
    variables = {"teamKey": team_key, "issueNumber": issue_number}
    payload = {"query": query, "variables": variables}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    matched_issues = response.json()["data"]["issues"]["nodes"]

    if len(matched_issues) == 0:
        return None
    else:
        return matched_issues[0]


def get_label_id(team_id, label_name):
    query = """
    query LabelsByTeam ($teamId: ID) {
        issueLabels(filter: {team: {id: {eq: $teamId}}}) {
            nodes {
                id,
                name
            }
        }
    }
    """
    variables = {"teamId": team_id}
    payload = {"query": query, "variables": variables}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    labels = response.json()["data"]["issueLabels"]["nodes"]
    matched_label = list(filter(lambda x: x["name"] == label_name, labels))

    if len(matched_label) == 0:
        return None
    else:
        return matched_label[0]["id"]


def add_labels(issue_id, label_ids):
    query = """
    mutation IssueUpdate ($issueId: String!, $labelIds: [String!])  {
        issueUpdate(
            id: $issueId,
            input: {
                labelIds: $labelIds
            }
        ) {
            success
            issue {
                id
            }
        }
    }
    """
    variables = {"labelIds": label_ids, "issueId": issue_id}
    payload = {"query": query, "variables": variables}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return None


def add_comment(issue_id, comment):
    query = """
    mutation CommentCreateInput ($issueId: String!, $body: String!)  {
        commentCreate(
            input: {
                issueId: $issueId,
                body: $body
            }
        ) {
            success
            comment {
                id
            }
        }
    }
    """
    variables = {"body": comment, "issueId": issue_id}
    payload = {"query": query, "variables": variables}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return None


def update_linear(branch, title, description, comment, label):

    ## Linear supports three ways to link issues with your pull requests:
    # Include *issue ID* in the branch name
    # Include *issue ID* in the PR title
    # Include *issue ID* with a magic word in the PR description (e.g. Fixes ENG-123) similar to GitHub Issues

    # Find issue through branch name
    match = re.search("(?i)(\w+)-(\d+)", branch)
    if not match:
        print("Unable to infer issue code from branch name", flush=True)

        # Find issue through branch name
        match = re.search("(?i)(\w+)-(\d+)", title)
        if not match:
            print("Unable to infer issue code from PR title", flush=True)

            # Find issue through pr description
            match = re.search("(?i)(\w+)-(\d+)", description)
            if not match:
                print("Unable to infer issue code from PR description", flush=True)
                sys.exit()

    # Extract team key and issue number
    team_key = match.group(1).upper()
    issue_number = int(match.group(2))

    # Get issue
    issue = get_issue(team_key, issue_number)
    if not issue:
        print("No matching issues found!", flush=True)
    issue_id = issue.get("id")
    team_id = issue.get("team").get("id")
    label_ids = list(set([label.get("id") for label in issue.get("labels").get("nodes")]))

    # Add comment
    add_comment(issue_id, comment)

    # Add label (if present)
    if label:

        # Get label id
        label_id = get_label_id(team_id, label)
        if not label_id:
            print("No matching labels found!", flush=True)
            sys.exit()
        label_ids.append(label_id)

        # Add label
        add_labels(issue_id, label_ids)


if __name__ == "__main__":

    try:
        update_linear(**args)
    except requests.HTTPError as e:
        print("API response: {}".format(e.response.text), flush=True)
        raise

    print("All done!")
