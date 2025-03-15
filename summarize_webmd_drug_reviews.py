#!/usr/bin/env -S uv run
# The comments below specify dependencies needed to run this project
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "llm>=0.23",
#   "pandas>=2.2.3",
#   "sqlite-utils>=3.38",
#   "markdown>=3.4.1"
# ]
# ///
import pandas as pd
import sqlite_utils
from sqlite_utils import Database
import llm

# type aliases
WordCount = int
DrugReview = str
DrugName = str
DrugSummary = str


def import_csv_to_sqlite_db(csv_path: str, table_name) -> Database:
    df = pd.read_csv(csv_path)
    print(f"Data set has {len(df)} rows, with columns: {list(df.columns)}")

    # Load/create a database file
    DB = sqlite_utils.Database("psych_med_reviews.sqlite")

    # Add to DB if it's not already there
    if table_name not in DB.table_names():
        DB[table_name].insert_all(df.to_dict(orient="records"))
    print(f"Database table {table_name} has {DB[table_name].count} rows")
    return DB


def extract_drug_info(DB: Database, table_name: str) -> dict[str, list[DrugReview]]:
    # Count words in reviews for each drug
    column_details = DB[table_name].analyze_column("drug_name")

    print(
        f"There are {column_details.num_distinct} unique medications in the database."
    )
    # Generate a dictionary of drug names and their associated notes
    drug_notes: dict[DrugName, list[DrugReview]] = {}
    for row in DB[table_name].rows:
        drug_name = row["drug_name"]
        note = row["text"]
        if drug_name not in drug_notes:
            drug_notes[drug_name] = []
        drug_notes[drug_name].append(note)

    return drug_notes


def fetch_llm_summaries(
    drug_info: dict[DrugName, list[DrugReview]], model_name: str
) -> dict[DrugName, DrugSummary]:
    llm_context_windows = {
        "deepseek-chat": 64_000,
        "gpt-4o-mini": 128_000,
        "anthropic/claude-3-5-haiku-latest": 200_000,
    }
    review_summaries: dict[DrugName, DrugSummary] = {}

    # Because words don't map perfectly to tokens, take a conservative
    # estimate of context window in terms of words
    est_max_words = llm_context_windows[model_name] * 0.6
    for drug, notes in drug_info.items():
        summary = submit_drug_review_and_join(model_name, drug, notes, est_max_words)
        review_summaries[drug] = summary

    return review_summaries


def submit_drug_review_and_join(
    model_name: str, drug_name: DrugName, notes: list[DrugReview], est_max_words: int
) -> DrugSummary:
    # Count words in the notes list and compare with the model's max context length.
    # Partition our notes into sub-lists that will fit inside the context length
    # Combine multiple reviews as needed
    sub_notes = [[]]
    word_count = 0
    for note in notes:
        note_wc = 0
        if note:
            note_wc = len(note.split())

        # start a new sub_note if we're over the word limit
        if word_count + note_wc > est_max_words:
            sub_notes.append([])
            word_count = 0
        sub_notes[-1].append(note)
        word_count += note_wc

    summaries = [
        fetch_summary(model_name, drug_name, sub_note) for sub_note in sub_notes
    ]
    summary = combine_summaries(model_name, summaries)
    return summary


def fetch_summary(
    model_name: str, drug_name: DrugName, notes: list[DrugReview]
) -> DrugSummary:
    prompt = summarization_prompt(drug_name) + "\n".join(
        [f"<review>{rev}</review>" for rev in notes]
    )
    model = llm.get_model(model_name)
    # ETJ DEBUG
    print(f"Submitting summary prompt for {drug_name} to {model_name}")
    # END DEBUG
    summary = model.prompt(prompt).text()

    return summary


def combine_summaries(model_name: str, summaries: list[DrugSummary]) -> DrugSummary:
    # If there's only a single summary (most common), just return it
    if len(summaries) == 1:
        return summaries[0]

    prompt = """ The following summaries represent a digest of patient
        experiences with a single drug. We've created the summaries by highlighting
        outstanding positive or negative experiences with the drug. Please combine
        all summaries into one super-summary of approximately the same length as
        a single summary. No need to mention similar symptoms (example: "mild headaches" 
        and "occasional migraines" should be treated as a single entry) twice, but
        if extraordinary experiences are present and distinct in multiple summaries,
        include them all.

        Summaries are delineated with <summary> and </summary>. They follow:
        
    """
    prompt_and_summaries = prompt + "\n".join(
        [f"<summary>{summary}</summary>" for summary in summaries]
    )
    model = llm.get_model(model_name)
    # ETJ DEBUG
    print(f"Submitting combination prompt for {len(summaries)} summaries")
    # END DEBUG
    response_text = model.prompt(prompt_and_summaries).text()
    return response_text


def summarization_prompt(drug_name: DrugName) -> str:
    review_prompt = f"""I'm appending a number of anonymized patient reviews for the 
    medication {drug_name} below. Please read the reviews and give me a short summary of 
    patients' feelings about the drug. You might list people's favorite good points,
    and least-liked elements about the experience. Pay attention to people who have 
    very strong positive or negative experiences, and include excerpts from those 
    reviews occasionally if they're very unusual. As an example, please don't include
    any excerpts about common mild symptoms, but if one user reports life-changing 
    headaches or amnesia, that's probably worth highlighting. Try to limit your summary
    to about two hundred words. 

    Return a summary in Markdown format with sections ## Positive, ## Negative, 
    ## Noteworthy (optional, include only for outlier experiences), and ## Conclusion

    Please don't introduce the summary, just begin right away.

    Reviews follow, and each is bracketed by <review> to start and </review> to end.


    """
    return review_prompt


def print_summaries(summaries: dict[DrugName, DrugSummary]):
    eq_line = "=" * 60 + "\n"
    for drug, summary in summaries.items():
        print(f"\n{eq_line}{drug}\n{eq_line}{summary}")


def create_summary_webapp(
    summaries: dict[DrugName, DrugSummary], output_dir: str = "summary_webapp"
):
    """
    Creates a web application to display drug summaries.

    Parameters:
    -----------
    summaries: dict[DrugName, DrugSummary]
        Dictionary mapping drug names to their markdown summaries
    output_dir: str, default="summary_webapp"
        Directory to create the web application in
    """
    import markdown
    import shutil
    from pathlib import Path

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True)

    # Create CSS file
    css_content = """
    :root {
        --bg-color: #1a2639;
        --text-color: #f8eeb4;
        --link-color: #91c7b1;
        --link-hover-color: #b9e6d3;
        --header-color: #3e4a61;
        --border-color: #3e4a61;
    }
    
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: var(--bg-color);
        color: var(--text-color);
        margin: 0;
        padding: 0;
        display: flex;
        min-height: 100vh;
    }
    
    .sidebar {
        width: 250px;
        background-color: var(--header-color);
        padding: 20px;
        box-sizing: border-box;
        position: fixed;
        height: 100vh;
        overflow-y: auto;
    }
    
    .sidebar h2 {
        margin-top: 0;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
    }
    
    .sidebar ul {
        list-style-type: none;
        padding: 0;
    }
    
    .sidebar li {
        margin-bottom: 10px;
    }
    
    .sidebar a {
        color: var(--link-color);
        text-decoration: none;
        display: block;
        padding: 5px;
        border-radius: 4px;
        transition: background-color 0.2s, color 0.2s;
    }
    
    .sidebar a:hover {
        background-color: rgba(255, 255, 255, 0.1);
        color: var(--link-hover-color);
    }
    
    .content {
        flex: 1;
        padding: 20px;
        margin-left: 250px;
        max-width: 800px;
    }
    
    h1, h2, h3 {
        color: var(--link-color);
    }
    
    a {
        color: var(--link-color);
    }
    
    a:hover {
        color: var(--link-hover-color);
    }
    
    .drug-title {
        margin-top: 0;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
    }
    
    blockquote {
        border-left: 4px solid var(--link-color);
        padding-left: 15px;
        margin-left: 0;
        font-style: italic;
    }
    """

    with open(output_path / "style.css", "w") as f:
        f.write(css_content)

    # Create menu HTML
    menu_html = """
    <div class="sidebar">
        <h2>Drug Summaries</h2>
        <ul>
            <li><a href="index.html">Introduction</a></li>
    """

    # Add links for each drug
    for drug_name in sorted(summaries.keys()):
        file_name = f"{drug_name.lower().replace(' ', '_')}.html"
        menu_html += f'        <li><a href="{file_name}">{drug_name}</a></li>\n'

    menu_html += """
        </ul>
    </div>
    """

    # Create HTML template
    html_template = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link rel="stylesheet" href="style.css">
    </head>
    <body>
        {menu}
        <div class="content">
            {content}
        </div>
    </body>
    </html>
    """

    # Create index page
    index_content = """
    <h1>WebMD Drug Reviews Summary</h1>
    <p>Welcome to the WebMD Drug Reviews Summary web application. This site provides summaries of patient reviews for various psychiatric medications.</p>
    <p>Each summary is generated using AI to analyze and synthesize patient experiences, highlighting both positive and negative aspects of each medication.</p>
    <p>Please select a medication from the menu on the left to view its summary.</p>
    <h2>About This Data</h2>
    <p>The summaries are based on real patient reviews from WebMD. These reviews represent personal experiences and should not be considered medical advice.</p>
    <p>Always consult with a healthcare professional before making any decisions about medications.</p>
    """

    index_html = html_template.format(
        title="WebMD Drug Reviews Summary", menu=menu_html, content=index_content
    )

    with open(output_path / "index.html", "w") as f:
        f.write(index_html)

    # Create a page for each drug
    for drug_name, summary in summaries.items():
        file_name = f"{drug_name.lower().replace(' ', '_')}.html"

        # Convert markdown to HTML
        html_content = markdown.markdown(summary)

        # Create the full HTML page
        drug_html = html_template.format(
            title=f"{drug_name} - Drug Summary",
            menu=menu_html,
            content=f"<h1 class='drug-title'>{drug_name}</h1>\n{html_content}",
        )

        with open(output_path / file_name, "w") as f:
            f.write(drug_html)

    print(f"Web application created in '{output_dir}' directory")
    print(f"Open '{output_dir}/index.html' in your browser to view the summaries")


def main():
    table_name = "webmd_reviews"
    model_name = "gpt-4o-mini"
    # Import dataset from .csv.gz file and save to a sqlite database
    db = import_csv_to_sqlite_db("psychiatric_drug_webmd_reviews.csv.zip", table_name)

    # Extract a dict of {drug_name: (word_count, notes_list)} for all drugs
    #   Possible Future refinement: our dataset has separate entries by dosage and
    #   application technique ("oral", "intramuscular") These might be reasonably
    #   combined into a single entry
    drug_info = extract_drug_info(db, table_name)

    # For debugging, let's just limit this dict to the first drug_subset entries
    drug_subset = len(drug_info)
    # drug_subset = 2  # Or comment out this line to run the entire dataset
    if drug_subset < len(drug_info):
        drug_info = dict(list(drug_info.items())[:drug_subset])

    # Create summary prompts and add in annotated note text for each drug
    # Note that we're limited by the context windows of our chosen LLM

    # Submit all drugs to LLM and get summaries back
    all_summaries = fetch_llm_summaries(drug_info, model_name)

    print_summaries(all_summaries)

    # Create a web application to display the summaries
    create_summary_webapp(all_summaries)


if __name__ == "__main__":
    main()
