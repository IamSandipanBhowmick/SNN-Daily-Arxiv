import datetime
import json
import arxiv
from pathlib import Path


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


def get_daily_papers(topic, query="SNN", max_results=2):
    """
    @param topic: str
    @param query: str
    @return data, data_web
    """

    content = {}
    content_to_web = {}

    search_engine = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    # New arxiv API fix
    client = arxiv.Client(
        page_size=100,
        delay_seconds=3,
        num_retries=3,
    )

    for result in client.results(search_engine):

        paper_id = result.get_short_id()
        paper_key = get_paper_key(paper_id)

        paper_title = result.title.replace("\n", " ")
        paper_url = result.entry_id
        paper_authors = get_authors(result.authors)
        paper_first_author = get_authors(result.authors, first_author=True)

        primary_category = result.primary_category
        publish_time = result.published.date()
        update_time = result.updated.date()

        print(
            "Time = ",
            update_time,
            " title = ",
            paper_title,
            " author = ",
            paper_first_author,
            " category = ",
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

        except Exception as e:
            print(f"exception: {e} with id: {paper_key}")

    sorted_content = dict(
        sorted(
            content.items(),
            key=lambda x: x[1].split("|")[1],
            reverse=True,
        )
    )

    sorted_content_to_web = dict(
        sorted(
            content_to_web.items(),
            key=lambda x: x[1].split(",")[0],
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

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            json_data = {}
        else:
            json_data = json.loads(content)

    for data in data_all:
        for keyword in data.keys():
            papers = data[keyword]

            if keyword in json_data.keys():
                json_data[keyword].update(papers)
            else:
                json_data[keyword] = papers

    for keyword in json_data.keys():
        papers = json_data[keyword]
        sorted_papers = dict(
            sorted(
                papers.items(),
                key=lambda x: x[1].split("|")[1],
                reverse=True,
            )
        )
        json_data[keyword] = sorted_papers

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)


def json_to_md(
    filename,
    md_filename,
    to_web=False,
    use_title=True,
    use_tc=True,
    show_badge=False,
):
    DateNow = datetime.date.today()
    DateNow = str(DateNow).replace("-", ".")

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            data = {}
        else:
            data = json.loads(content)

    with open(md_filename, "w", encoding="utf-8") as f:

        if use_title and to_web:
            f.write("---\n")
            f.write("layout: default\n")
            f.write("---\n\n")

        if show_badge:
            f.write("[![Contributors][contributors-shield]][contributors-url]\n")
            f.write("[![Forks][forks-shield]][forks-url]\n")
            f.write("[![Stargazers][stars-shield]][stars-url]\n")
            f.write("[![Issues][issues-shield]][issues-url]\n\n")

        if use_title:
            f.write("## Updated on " + DateNow + "\n\n")
        else:
            f.write("> Updated on " + DateNow + "\n\n")

        if use_tc:
            f.write("<details>\n")
            f.write("  <summary>Table of Contents</summary>\n")
            f.write("  <ol>\n")

            for keyword in data.keys():
                day_content = data[keyword]
                if not day_content:
                    continue

                kw = keyword.replace(" ", "-")
                f.write(f"    <li><a href=#{kw}>{keyword}</a></li>\n")

            f.write("  </ol>\n")
            f.write("</details>\n\n")

        for keyword in data.keys():
            day_content = data[keyword]

            if not day_content:
                continue

            f.write(f"## {keyword}\n\n")

            if use_title:
                if not to_web:
                    f.write(
                        "|Publish Date|Title|Authors|Paper|\n"
                        "|---|---|---|---|\n"
                    )
                else:
                    f.write("| Publish Date | Title | Authors | Paper |\n")
                    f.write("|:---------|:-----------------------|:---------|:------|\n")

            for _, v in day_content.items():
                if v is not None:
                    f.write(v)

            f.write("\n")

            top_info = f"#Updated on {DateNow}"
            top_info = top_info.replace(" ", "-").replace(".", "")
            f.write(f"<p align=right>(<a href={top_info}>back to top</a>)</p>\n\n")

        if show_badge:
            f.write(
                "[contributors-shield]: "
                "https://img.shields.io/github/contributors/SpikingChen/snn-arxiv-daily.svg?style=for-the-badge\n"
            )
            f.write(
                "[contributors-url]: "
                "https://github.com/SpikingChen/snn-arxiv-daily/graphs/contributors\n"
            )
            f.write(
                "[forks-shield]: "
                "https://img.shields.io/github/forks/SpikingChen/snn-arxiv-daily.svg?style=for-the-badge\n"
            )
            f.write(
                "[forks-url]: "
                "https://github.com/SpikingChen/snn-arxiv-daily/network/members\n"
            )
            f.write(
                "[stars-shield]: "
                "https://img.shields.io/github/stars/SpikingChen/snn-arxiv-daily.svg?style=for-the-badge\n"
            )
            f.write(
                "[stars-url]: "
                "https://github.com/SpikingChen/snn-arxiv-daily/stargazers\n"
            )
            f.write(
                "[issues-shield]: "
                "https://img.shields.io/github/issues/SpikingChen/snn-arxiv-daily.svg?style=for-the-badge\n"
            )
            f.write(
                "[issues-url]: "
                "https://github.com/SpikingChen/snn-arxiv-daily/issues\n\n"
            )

    print("finished")


if __name__ == "__main__":

    data_collector = []
    data_collector_web = []

    keywords = {}

    keywords["Spiking Neural Network"] = (
        '"Spiking Neural Network" OR '
        '"Spiking Neural Networks" OR '
        '"Spiking Neuron" OR '
        '"Spiking Neural Nets" OR '
        '"SNN"'
    )

    for topic, keyword in keywords.items():

        print("Keyword: " + topic)

        data, data_web = get_daily_papers(
            topic,
            query=keyword,
            max_results=200,
        )

        data_collector.append(data)
        data_collector_web.append(data_web)

        print("\n")

    json_file = "snn-arxiv-daily.json"
    md_file = "README.md"

    update_json_file(json_file, data_collector)

    json_to_md(json_file, md_file)

