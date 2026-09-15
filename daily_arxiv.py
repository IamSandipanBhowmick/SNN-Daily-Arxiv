import datetime
import json
import time
from pathlib import Path

import arxiv


def get_authors(authors, first_author=False):
    if not authors:
        return "Unknown"

    if first_author:
        return str(authors[0])

    return ", ".join(str(author) for author in authors)


def get_paper_key(paper_id):
    """
    Example:
    2108.09112v1 -> 2108.09112
    """

    ver_pos = paper_id.find("v")

    if ver_pos == -1:
        return paper_id

    return paper_id[:ver_pos]


def fetch_arxiv_results(search_engine, attempts=3):
    """
    Fetch arXiv results with bounded retries.

    The function retries HTTP 429 errors three times,
    waiting 10 seconds between attempts. If arXiv remains
    unavailable, it returns an empty list.
    """

    client = arxiv.Client(
        page_size=100,
        delay_seconds=5,
        num_retries=0,
    )

    for attempt in range(1, attempts + 1):
        try:
            return list(client.results(search_engine))

        except arxiv.HTTPError as exc:
            error_message = str(exc)

            if "429" not in error_message:
                print(f"::warning::arXiv API error: {exc}")
                return []

            if attempt == attempts:
                print(
                    "::warning::arXiv is still rate-limiting requests "
                    "after three attempts. Skipping today's update."
                )
                return []

            print(
                f"arXiv rate limit detected "
                f"(attempt {attempt}/{attempts}). "
                "Retrying in 10 seconds..."
            )

            time.sleep(10)

        except Exception as exc:
            print(f"::warning::Unexpected arXiv error: {exc}")
            return []

    return []


def get_daily_papers(topic, query="SNN", max_results=100):
    """
    Collect the newest papers returned by the arXiv API.

    Parameters
    ----------
    topic : str
        Display name of the paper category.
    query : str
        arXiv search query.
    max_results : int
        Maximum number of papers requested.

    Returns
    -------
    data, data_web : tuple
        Paper information for README and web output.
    """

    content = {}
    content_to_web = {}

    search_engine = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    results = fetch_arxiv_results(search_engine)

    if not results:
        print(
            f"No new data retrieved for '{topic}'. "
            "Existing data will remain unchanged."
        )
        return {topic: {}}, {topic: {}}

    for result in results:
        paper_id = result.get_short_id()
        paper_key = get_paper_key(paper_id)

        paper_title = result.title.replace("\n", " ").replace("|", "\\|")
        paper_url = result.entry_id

        paper_first_author = get_authors(
            result.authors,
            first_author=True,
        )

        primary_category = result.primary_category
        update_time = result.updated.date()

        print(
            "Time =",
            update_time,
            "title =",
            paper_title,
            "author =",
            paper_first_author,
            "category =",
            primary_category,
        )

        try:
            content[paper_key] = (
                f"|**{update_time}**|"
                f"**{paper_title}**|"
                f"{paper_first_author} et al.|"
                f"[{paper_id}]({paper_url})|\n"
            )

            content_to_web[paper_key] = (
                f"- {update_time}, **{paper_title}**, "
                f"{paper_first_author} et al., "
                f"Paper: [{paper_url}]({paper_url})\n"
            )

        except Exception as exc:
            print(
                f"Exception while processing paper {paper_key}: {exc}"
            )

    sorted_content = dict(
        sorted(
            content.items(),
            key=lambda item: item[1].split("|")[1],
            reverse=True,
        )
    )

    sorted_content_to_web = dict(
        sorted(
            content_to_web.items(),
            key=lambda item: item[1].split(",")[0],
            reverse=True,
        )
    )

    data = {topic: sorted_content}
    data_web = {topic: sorted_content_to_web}

    return data, data_web


def update_json_file(filename, data_all):
    file_path = Path(filename)

    if not file_path.exists():
        file_path.write_text("{}", encoding="utf-8")

    with open(filename, "r", encoding="utf-8") as file:
        content = file.read().strip()

        if not content:
            json_data = {}
        else:
            json_data = json.loads(content)

    for data in data_all:
        for keyword, papers in data.items():
            if keyword in json_data:
                json_data[keyword].update(papers)
            else:
                json_data[keyword] = papers

    for keyword in json_data:
        papers = json_data[keyword]

        sorted_papers = dict(
            sorted(
                papers.items(),
                key=lambda item: item[1].split("|")[1],
                reverse=True,
            )
        )

        json_data[keyword] = sorted_papers

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(
            json_data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def json_to_md(
    filename,
    md_filename,
    to_web=False,
    use_title=True,
    use_tc=True,
    show_badge=False,
):
    date_now = str(datetime.date.today()).replace("-", ".")

    with open(filename, "r", encoding="utf-8") as file:
        content = file.read().strip()

        if not content:
            data = {}
        else:
            data = json.loads(content)

    with open(md_filename, "w", encoding="utf-8") as file:
        if use_title and to_web:
            file.write("---\n")
            file.write("layout: default\n")
            file.write("---\n\n")

        if show_badge:
            file.write(
                "[![Contributors][contributors-shield]]"
                "[contributors-url]\n"
            )
            file.write(
                "[![Forks][forks-shield]]"
                "[forks-url]\n"
            )
            file.write(
                "[![Stargazers][stars-shield]]"
                "[stars-url]\n"
            )
            file.write(
                "[![Issues][issues-shield]]"
                "[issues-url]\n\n"
            )

        if use_title:
            file.write(f"## Updated on {date_now}\n\n")
        else:
            file.write(f"> Updated on {date_now}\n\n")

        if use_tc:
            file.write("<details>\n")
            file.write("  <summary>Table of Contents</summary>\n")
            file.write("  <ol>\n")

            for keyword, day_content in data.items():
                if not day_content:
                    continue

                keyword_anchor = keyword.replace(" ", "-")

                file.write(
                    f'    <li><a href="#{keyword_anchor}">'
                    f"{keyword}</a></li>\n"
                )

            file.write("  </ol>\n")
            file.write("</details>\n\n")

        for keyword, day_content in data.items():
            if not day_content:
                continue

            file.write(f"## {keyword}\n\n")

            if use_title:
                if not to_web:
                    file.write(
                        "|Publish Date|Title|Authors|Paper|\n"
                        "|---|---|---|---|\n"
                    )
                else:
                    file.write(
                        "| Publish Date | Title | Authors | Paper |\n"
                    )
                    file.write(
                        "|:---------|:-----------------------|"
                        ":---------|:------|\n"
                    )

            for value in day_content.values():
                if value is not None:
                    file.write(value)

            file.write("\n")

            top_info = f"#Updated on {date_now}"
            top_info = top_info.replace(" ", "-").replace(".", "")

            file.write(
                f'<p align="right">(<a href="{top_info}">'
                "back to top</a>)</p>\n\n"
            )

        if show_badge:
            file.write(
                "[contributors-shield]: "
                "https://img.shields.io/github/contributors/"
                "SpikingChen/snn-arxiv-daily.svg"
                "?style=for-the-badge\n"
            )

            file.write(
                "[contributors-url]: "
                "https://github.com/SpikingChen/"
                "snn-arxiv-daily/graphs/contributors\n"
            )

            file.write(
                "[forks-shield]: "
                "https://img.shields.io/github/forks/"
                "SpikingChen/snn-arxiv-daily.svg"
                "?style=for-the-badge\n"
            )

            file.write(
                "[forks-url]: "
                "https://github.com/SpikingChen/"
                "snn-arxiv-daily/network/members\n"
            )

            file.write(
                "[stars-shield]: "
                "https://img.shields.io/github/stars/"
                "SpikingChen/snn-arxiv-daily.svg"
                "?style=for-the-badge\n"
            )

            file.write(
                "[stars-url]: "
                "https://github.com/SpikingChen/"
                "snn-arxiv-daily/stargazers\n"
            )

            file.write(
                "[issues-shield]: "
                "https://img.shields.io/github/issues/"
                "SpikingChen/snn-arxiv-daily.svg"
                "?style=for-the-badge\n"
            )

            file.write(
                "[issues-url]: "
                "https://github.com/SpikingChen/"
                "snn-arxiv-daily/issues\n\n"
            )

    print("Finished generating README.md")


if __name__ == "__main__":
    data_collector = []
    data_collector_web = []

    keywords = {
        "Spiking Neural Network": (
            '"Spiking Neural Network" OR '
            '"Spiking Neural Networks" OR '
            '"Spiking Neuron" OR '
            '"Spiking Neural Nets" OR '
            '"SNN"'
        )
    }

    for topic, keyword in keywords.items():
        print(f"Keyword: {topic}")

        data, data_web = get_daily_papers(
            topic=topic,
            query=keyword,
            max_results=100,
        )

        data_collector.append(data)
        data_collector_web.append(data_web)

        print()

    json_file = "snn-arxiv-daily.json"
    md_file = "README.md"

    update_json_file(
        filename=json_file,
        data_all=data_collector,
    )

    json_to_md(
        filename=json_file,
        md_filename=md_file,
    )
