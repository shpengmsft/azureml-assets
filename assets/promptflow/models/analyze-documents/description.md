The "Analyze Documents" is a standard model that utilizes Azure AI Language to perform various analyzes on text-based documents. Azure AI language hosts pre-trained, task-oriented, and optimized document focused ML models, such as summarization, sentiment analysis, entity extraction, etc. 


### Inference samples

Inference type|CLI|VS Code Extension
|--|--|--|
Real time|<a href="https://microsoft.github.io/promptflow/how-to-guides/deploy-a-flow/index.html" target="_blank">deploy-promptflow-model-cli-example</a>|<a href="https://microsoft.github.io/promptflow/how-to-guides/deploy-a-flow/index.html" target="_blank">deploy-promptflow-model-vscode-extension-example</a>
Batch | N/A | N/A

### Sample inputs and outputs (for real-time inference)

#### Sample input
```json
{
    "inputs": {
        "document_path": "<path_to_txt_file>",
        "language": "en"
    }
}
```

#### Sample output
Note: output has been shortened.
```json
{
    "outputs": {
      "extractive_summary": {
        "id": "2",
        "sentences": [
          {
            "text": "\"With *********, we're making the era of AI real for ****** and businesses around the world,\" said *************, ********* and *********************** of *********.",
            "rankScore": 0.62,
            "offset": 682,
            "length": 165
          },
          {
            "text": "\"We're rapidly infusing AI into every layer of the tech stack and for every function and business process to drive increased productivity for our *********.\"",
            "rankScore": 1,
            "offset": 848,
            "length": 157
          },
          {
            "text": "Pacific time (5:30 p.m. Eastern time) ***** to discuss details of the company's performance for the quarter and certain forward-looking information.",
            "rankScore": 0.98,
            "offset": 4290,
            "length": 148
          }
        ],
        "warnings": []
      },
      "abstractive_summary": {
        "summaries": [
          {
            "text": "The company announced the results for the quarter ended ******************, with revenue, operating income, net income, and diluted earnings per share. The company returned $9.1 billion to its share buybacks and dividends in the first quarter of 2024.",
            "contexts": [
              {
                "offset": 0,
                "length": 11915
              }
            ]
          }
        ],
        "id": "2",
        "warnings": []
      },
      "sentiment": {
        "id": "3",
        "sentiment": "neutral",
        "confidenceScores": {
          "positive": 0.02,
          "neutral": 0.96,
          "negative": 0.02
        },
        "sentences": [
          {
            "sentiment": "neutral",
            "confidenceScores": {
              "positive": 0.02,
              "neutral": 0.95,
              "negative": 0.04
            },
            "offset": 0,
            "length": 152,
            "text": "The company announced the results for the quarter ended ******************, with revenue, operating income, net income, and diluted earnings per share. "
          },
          {
            "sentiment": "neutral",
            "confidenceScores": {
              "positive": 0.01,
              "neutral": 0.97,
              "negative": 0.01
            },
            "offset": 152,
            "length": 99,
            "text": "The company returned $9.1 billion to its share buybacks and dividends in the first quarter of 2024."
          }
        ],
        "warnings": []
      },
      "recognized_entities": {
        "id": "2",
        "entities": [
          {
            "text": "AI",
            "category": "Skill",
            "type": "Skill",
            "offset": 872,
            "length": 2,
            "confidenceScore": 1,
            "tags": [
              {
                "name": "Skill",
                "confidenceScore": 1
              }
            ]
          }
        ],
        "warnings": []
      },
      "pii": {
        "redactedText": "********* Cloud Strength Drives First-Quarter Results\n**************** | *********************\nShare on ******** (opens new window)\n \nShare on ******** (opens new window)\n \nShare on ******* (opens new window)\nREDMOND, Wash. — ************* — *************** ***** announced the following results for the quarter ended ******************, compared to the corresponding period of the prior fiscal year:\n\nRevenue was $56.5 billion, up 13% (up 12% in constant currency)\nOperating income was $26.9 billion, up 25% (up 24% in constant currency)\nNet income was $22.3 billion, up 27% (up 26% in constant currency)\nDiluted earnings per share were $2.99, up 27% (up 26% in constant currency)\n\"With *********, we're making the era of AI real for ****** and businesses around the world,\" said *************, ********* and *********************** of *********. \"We're rapidly infusing AI into every layer of the tech stack and for every function and business process to drive increased productivity for our *********.\"\n\n\"Consistent execution by our sales teams and ******** drove a strong start to the fiscal year with ********* Cloud revenue of $31.8 billion, up 24% (up 23% in constant currency) year-over-year,\" said ********, ************************ and *********************** at *********.",
        "id": "1",
        "entities": [
          {
            "text": "Microsoft",
            "category": "Organization",
            "offset": 0,
            "length": 9,
            "confidenceScore": 0.66
          }
          {
            "text": "http://www.microsoft.com/en-us/investor.",
            "category": "URL",
            "offset": 11875,
            "length": 40,
            "confidenceScore": 0.8
          }
        ],
        "warnings": []
      }
    }
}
```