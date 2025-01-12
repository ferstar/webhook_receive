import os
import sys
from datetime import datetime
from functools import cached_property
from pathlib import Path
import requests
from pydantic import BaseModel, computed_field, ConfigDict

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class Issue:
    def __init__(self, issue_id):
        self.id = issue_id
        self.dst_url = f"https://api.github.com/repos/ferstar/blog/issues/{issue_id}"
        self.headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    @property
    def is_valid(self):
        return self.check(self.issue)

    @staticmethod
    def check(item):
        return (
            item
            and item.get("author_association") == "OWNER"
            and not item.get("body", "").startswith("@")
        )

    @property
    def url(self):
        return self.issue.get("html_url")

    @cached_property
    def issue(self):
        return self.fetch_issue()

    @cached_property
    def comments(self):
        url = self.issue.get("comments_url") or ""
        return self.fetch_comments(url) or []

    def fetch_issue(self):
        rsp = requests.get(self.dst_url, headers=self.headers)
        if rsp.status_code == 200:
            return rsp.json()
        raise Exception(rsp.text)

    def fetch_comments(self, comments_url):
        rsp = requests.get(comments_url, headers=self.headers)
        if rsp.status_code == 200:
            comments = rsp.json()
            ret = []
            for comment in comments:
                if self.check(comment):
                    ret.append(comment)

            return ret
        raise Exception(rsp.text)


class Article(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _from_p = "%Y-%m-%dT%H:%M:%SZ"
    _to_f = "%Y-%m-%dT%H:%M:%S+08:00"
    issue: Issue

    @computed_field
    @property
    def title(self) -> str:
        return self.issue.issue.get("title")

    @computed_field
    @property
    def comment_url(self) -> str:
        return self.issue.url

    @computed_field
    @property
    def tags(self) -> list[str]:
        tags = []
        for label in self.issue.issue.get("labels", []):
            tags.append(label["name"])
        return tags if tags else ["Default"]

    @computed_field
    @property
    def created_at(self) -> str:
        created_at = self.issue.issue["created_at"]
        return datetime.strptime(created_at, self._from_p).strftime(self._to_f)

    @computed_field
    @property
    def updated_at(self) -> str:
        updated_at = self.issue.issue["updated_at"]
        if self.issue.comments:
            c_updated_at = self.issue.comments[(-1)]["updated_at"]
        else:
            c_updated_at = updated_at
        updated_at = datetime.strptime(updated_at, self._from_p)
        c_updated_at = datetime.strptime(c_updated_at, self._from_p)
        if c_updated_at > updated_at:
            updated_at = c_updated_at
        return updated_at.strftime(self._to_f)

    @computed_field
    @property
    def body(self) -> str:
        meta = f'---\ntitle: "{self.title}"\ndate: "{self.created_at}"\ntags: {self.tags}\ncomments: true\n---'
        quote = f"---\n\n```js\nNOTE: I am not responsible for any expired content.\nCreated at: {self.created_at}\nUpdated at: {self.updated_at}\nOrigin issue: {self.comment_url}\n```"
        main_body = f"{self.issue.issue.get('body').rstrip()}"
        comment_body = "\n\n".join(
            [item["body"].rstrip() for item in self.issue.comments]
        ).rstrip()
        return f"{meta}\n\n{main_body}\n\n{comment_body}\n\n{quote}\n"

    def dump2md(self, parent_dir):
        path = parent_dir / f"issue-{self.issue.id}.md"
        path.write_text(self.body)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 2:
        print("Usage: python convert_issue_to_md.py <issue_id> <output_dir>")
        sys.exit(1)
    issue_id, output_dir = args
    article = Article(issue=Issue(issue_id))
    article.dump2md(Path(output_dir))
