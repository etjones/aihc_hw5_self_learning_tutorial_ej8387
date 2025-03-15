autoscale: true
theme: next, 1
code-language: Python

## AI In Healthcare, Homework 5: Self-Learning Tutorial
### [Evan Jones](mailto:evan_jones@utexas.edu), UT ID:  `ej8387`

---

# 1: Project Overview
<a name="project_overview"/>

This guide is in five parts:
1. [Project Overview](#project_overview)
2. [Project Setup](#project_setup)
3. [Dataset Ingestion](#dataset_ingestion)
4. [LLM Summarization](#llm_summarization)
5. [Final Presentation](#final_presentation)

---

# Side Effects Can Ruin Your Life
In 2002, my friend David MacLean woke up in a train station in Hydrabad, India.

He didn't know why he was there.

He didn't know his own name.

His entire past had disappeared.

---

# Loss and recovery

A kind policeman helped him find his home. 
He discovered that he was American,  on a Fulbright scholarship to study in India. 
And he discovered that he'd been taking [Lariam (Mefloquine)](https://en.wikipedia.org/wiki/Mefloquine), 
an antimalarial medication recommended by the  U.S. Government. 

Eventually, he discovered that Lariam was linked to murders, suicides, and amnesia
like his own. He told his story on the national radio program, [This American Life](https://www.thisamericanlife.org/399/contents-unknown/act-three), and wrote a book, [The Answer to the Riddle is Me](https://en.wikipedia.org/wiki/The_Answer_to_the_Riddle_Is_Me). He slowly pieced his life together.

![right fit](assets/the_answer_to_the_riddle_is_me_cover.jpg)

---

# Identifying Long-tail Side Effects with LLMs

Side effects like David's are rare. 
But when many people take a medication, even "rare" side effects happen quite often. 

Small text warnings on a drug label can't prepare you for the impact a medicine might have on your life.

This project uses Large Language Models (LLMs) to summarize patient reviews for psychoactive medications and highlight outlier experiences, good or bad.


--- 

# 2: Project Setup
<a name="project_setup"/>

install UV & Python
clone project
set up environment
Configure `llm` for your LLM

--- 

# Install the [`llm`](https://llm.datasette.io/en/stable/) tool

[Simon Willison's](https://simonwillison.net/) [`llm`](https://llm.datasette.io/en/stable/) tool is a Swiss Army knife for working with large language models. Install it with `pip` or [`uv`](https://docs.astral.sh/uv/):

``` shell
pip install llm
```

--- 

# Request an API Key for your LLM 

[Claude](https://claude.ai/new) and [DeepSeek](https://chat.deepseek.com/), and [ChatGPT] are capable, affordable, LLMs. You may need to set up accounts and credit cards for billing first.

[Anthropic API Keys Page](https://console.anthropic.com/settings/keys)
[DeepSeek API Keys Page](https://platform.deepseek.com/api_keys)
[OpenAI API Keys Page](https://platform.openai.com/settings/organization/api-keys)

**LLM API Costs, 2025-03-15**

| LLM | Input cost, 1M tokens | Output cost, 1M tokens | Max Context Window, tokens
| -------- | -------- | -------- | -------- |
| [Anthropic Haiku 3.5](https://www.anthropic.com/pricing#anthropic-api)   | $0.80    | $4.00    | 200K
| [DeepSeek-Chat](https://api-docs.deepseek.com/quick_start/pricing/)   | $0.07   | $1.10   | 64K
| [OpenAI GPT-4o Mini](https://openai.com/api/pricing/) | $0.15 | $0.60 | 128K

![left fit](assets/anthropic_api_key_page.png)
![right fit](assets/deepseek_api_key_page.png)


--- 

# Manage API Keys with `llm`

`llm` has several [mechanisms](https://llm.datasette.io/en/stable/setup.html#api-key-management) to manage API keys. You can set and forget by running:

```shell
llm set keys anthropic
```
 or

 ```shell
llm set keys deepseek
```


---

# Install LLM-specific `llm` plugins
`llm` comes configured to use OpenAI's ChatGPT. It's easy to [set up other LLMs](https://llm.datasette.io/en/stable/plugins/installing-plugins.html#installing-plugins), though:

```shell
llm install llm-anthropic
llm install llm-deepseek
```

--- 

# 3. Dataset Ingestion
<a name="dataset_ingestion"/>

--- 

# 4. LLM Summarization
<a name="llm_summarization"/>

---

# 5. Final Presentation
<a name="final_presentation"/>
Once we've created all our LLM summaries, we're left with a dictionary of 
`{drug_name: drug_summary_markdown}` pairs. Let's improve the presentation!

--- 

# Create a minimal Web app
I'm not much of a web programmer, but Claude is. I used the following prompt
to make a function that makes a passable-looking, vanilla HTML web app:

```
make a function that accepts a dict of {drug_name: markdown_summary} pairs and writes a directory called summary_webapp that contains a plain vanilla html page for each drug_name, renders the markdown_summary (which is in markdown) to HTML. There should also be an index.html page that contains an introduction, and all pages should have a menu column on the left side linking to each drug_name page. Let's not duplicate the menu on each page-- we should be able to use one menu list throughout the entire app. We should also include CSS that applies to the entire web app and defaults to sans-serif yellow-ish text on a darker blue backgrond-- but make sure the color palettes are appealing and use web standards
```

The result was about 200 lines of code, `create_summary_webapp()` and worked
on the first try.

![fit](assets/web_app_intro_page.png)