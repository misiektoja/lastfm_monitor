"""Documentation site structure, its internal links and the links that point into it from the rest of the repository."""

import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

sys.path.insert(0, str(PROJECT_ROOT))

import lastfm_monitor  # noqa: E402

# Every page the site publishes, so a page added or renamed without a nav entry fails here
EXPECTED_PAGES = ("about.md", "configuration.md", "index.md", "installation.md", "setup-and-first-run.md", "testing.md", "troubleshooting.md", "usage.md")

# Documents outside docs/ that send a reader into the documentation, which no site link check ever opens
REPOSITORY_DOCUMENTS = ("README.md", "SUPPORT.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "THIRD_PARTY_NOTICES.md", ".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/config.yml", ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/feature_request.yml", "tests/README.md")

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


# Returns the lines of a markdown document that sit outside fenced code blocks, so a shell comment is not read as a heading
def lines_outside_fences(text):
    lines, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            lines.append(line)
    return lines


# Returns the anchor slug MkDocs generates for one heading
def heading_anchor(heading):
    return re.sub(r"[^a-z0-9 _-]", "", heading.strip().lower()).replace(" ", "-")


# Returns every anchor a page offers, which is one per heading below the title
def page_anchors(path):
    return {heading_anchor(line.lstrip("#").strip()) for line in lines_outside_fences(path.read_text(encoding="utf-8")) if line.startswith("##")}


ALL_ANCHORS = {path.name: page_anchors(path) for path in DOCS_DIR.glob("*.md")}


class TestSiteStructure:
    def test_the_published_page_set_is_pinned(self):
        assert tuple(sorted(path.name for path in DOCS_DIR.glob("*.md"))) == EXPECTED_PAGES

    def test_every_page_is_listed_in_the_navigation(self):
        nav = (PROJECT_ROOT / "mkdocs.yml").read_text(encoding="utf-8").split("nav:", 1)[1]
        for page in EXPECTED_PAGES:
            assert re.search(rf": +{re.escape(page)}\s*$", nav, re.M), f"{page} is missing from the mkdocs nav"

    @pytest.mark.parametrize("page", EXPECTED_PAGES)
    def test_each_page_has_exactly_one_title(self, page):
        titles = [line for line in lines_outside_fences((DOCS_DIR / page).read_text(encoding="utf-8")) if line.startswith("# ")]
        assert len(titles) == 1, f"{page} has {len(titles)} level-one headings: {titles}"

    # A split README can land the same section on two pages, which no link check and no site build notices
    def test_no_section_appears_on_two_pages(self):
        seen = {}
        for page in EXPECTED_PAGES:
            for line in lines_outside_fences((DOCS_DIR / page).read_text(encoding="utf-8")):
                if line.startswith("## "):
                    seen.setdefault(line[3:].strip(), []).append(page)
        duplicated = {section: pages for section, pages in seen.items() if len(pages) > 1}
        assert duplicated == {}, f"sections on more than one page: {duplicated}"


class TestSiteLinks:
    @pytest.mark.parametrize("page", EXPECTED_PAGES)
    def test_every_local_link_resolves_to_a_page_and_an_anchor(self, page):
        for target in MARKDOWN_LINK.findall((DOCS_DIR / page).read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            document, _, anchor = target.partition("#")
            resolved = page if not document else document
            assert (DOCS_DIR / resolved).is_file() or (DOCS_DIR / resolved).is_dir(), f"{page} links to missing '{target}'"
            if anchor and resolved.endswith(".md"):
                assert anchor in ALL_ANCHORS[resolved], f"{page} links to missing anchor '{target}'"


class TestLinksIntoTheDocumentation:
    # A site link check walks only the pages it publishes, so the links pointing into them from the repository rot unnoticed
    @pytest.mark.parametrize("document", REPOSITORY_DOCUMENTS)
    def test_no_repository_document_links_to_a_removed_readme_anchor(self, document):
        path = PROJECT_ROOT / document
        assert path.is_file(), f"{document} is missing"
        readme_anchors = page_anchors(PROJECT_ROOT / "README.md")
        text = path.read_text(encoding="utf-8")
        for anchor in re.findall(r"(?:README\.md|/lastfm_monitor)#([a-z0-9-]+)", text):
            assert anchor in readme_anchors, f"{document} links to README anchor '#{anchor}', which the landing page no longer has"

    @pytest.mark.parametrize("document", REPOSITORY_DOCUMENTS)
    def test_every_documentation_site_link_names_a_published_page(self, document):
        text = (PROJECT_ROOT / document).read_text(encoding="utf-8")
        for path_part, anchor in re.findall(rf"{re.escape(lastfm_monitor.DOCS_BASE_URL)}/([a-z0-9-]*)/?#?([a-z0-9-]*)", text):
            if not path_part:
                continue
            page = f"{path_part}.md"
            assert page in EXPECTED_PAGES, f"{document} links to '{path_part}/', which the site does not publish"
            assert not anchor or anchor in ALL_ANCHORS[page], f"{document} links to missing anchor '{path_part}/#{anchor}'"


class TestGuideConstants:
    # Every guide constant is a claim that a page and an anchor exist, and nothing else checks it
    @pytest.mark.parametrize("name", sorted(name for name in vars(lastfm_monitor) if name.endswith("_GUIDE_URL")))
    def test_each_guide_constant_resolves_to_a_published_page_and_anchor(self, name):
        url = getattr(lastfm_monitor, name)
        assert url.startswith(f"{lastfm_monitor.DOCS_BASE_URL}/"), f"{name} does not point at the documentation site"
        remainder = url[len(lastfm_monitor.DOCS_BASE_URL) + 1:]
        path_part, _, anchor = remainder.partition("#")
        path_part = path_part.strip("/")
        if not path_part:
            assert not anchor, f"{name} puts an anchor on the site root"
            return
        page = f"{path_part}.md"
        assert page in EXPECTED_PAGES, f"{name} names '{path_part}/', which the site does not publish"
        assert not anchor or anchor in ALL_ANCHORS[page], f"{name} names anchor '#{anchor}', which {page} does not have"

    # A constant nothing reads is a guide nobody is ever shown
    @pytest.mark.parametrize("name", sorted(name for name in vars(lastfm_monitor) if name.endswith("_GUIDE_URL")))
    def test_each_guide_constant_is_read_somewhere(self, name):
        source = (PROJECT_ROOT / "lastfm_monitor.py").read_text(encoding="utf-8")
        assert len(re.findall(rf"\b{name}\b", source)) > 1, f"{name} is defined but never used"
