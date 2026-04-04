<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Actions Cheatsheet</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: #f8f9fa;
        }
        header {
            text-align: center;
            margin-bottom: 50px;
            border-bottom: 3px solid #b31b1b; /* Cornell Red */
            padding-bottom: 20px;
        }
        h1 {
            margin: 0;
            font-size: 2.5rem;
            color: #222;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .credits {
            color: #666;
            margin-top: 10px;
            font-size: 0.9rem;
        }
        .credits a {
            color: #b31b1b;
            text-decoration: none;
        }
        .container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: white;
            border-radius: 8px;
            overflow: hidden; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
            display: flex;
            flex-direction: column;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card-header {
            background-color: #b31b1b; /* Cornell Red */
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .card-header h3 {
            margin: 0;
            color: white; 
            font-size: 1.4rem;
            letter-spacing: 0.5px;
            flex-grow: 1;
        }
        .card-icon {
            font-size: 1.6rem;
        }
        .card-body {
            padding: 24px;
            flex-grow: 1;
        }
        .description {
            font-size: 1rem;
            margin: 0 0 15px 0;
            color: #444;
        }
        .example {
            font-size: 0.85rem;
            color: #777;
            font-style: italic;
            border-top: 1px solid #eee;
            padding-top: 10px;
            margin: 0;
        }
        footer {
            text-align: center;
            margin-top: 60px;
            font-size: 0.8rem;
            color: #999;
        }
    </style>
</head>
<body>

    <header>
        <h1>LLM Actions Cheatsheet</h1>
        <div class="credits">
            <strong>Author:</strong> Tim Fraser, Systems Engineering<br>
            <a href="mailto:tmf77@cornell.edu">tmf77@cornell.edu</a>
        </div>
    </header>

    <div class="container">

        <div class="card">
            <div class="card-header">
                <span class="card-icon">🏷️</span>
                <h3>CLASSIFY</h3>
            </div>
            <div class="card-body">
                <p class="description">Categorizing and labeling input into a specific taxonomy or bucket.</p>
                <p class="example">Examples: Sentiment analysis, intent detection, tagging support tickets.</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-icon">✅</span>
                <h3>EVALUATE</h3>
            </div>
            <div class="card-body">
                <p class="description">Judging and scoring input against a rubric, logic gates, or specific criteria.</p>
                <p class="example">Examples: Grading essays, checking code for security flaws, compliance auditing.</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-icon">✍️</span>
                <h3>EDIT</h3>
            </div>
            <div class="card-body">
                <p class="description">Modifying existing content to improve quality, fix errors, or meet new constraints.</p>
                <p class="example">Examples: Grammar correction, rewriting for clarity, updating stale documentation.</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-icon">📝</span>
                <h3>SUMMARIZE</h3>
            </div>
            <div class="card-body">
                <p class="description">Condensing and distilling large volumes of text while preserving core intent.</p>
                <p class="example">Examples: Meeting minutes, TL;DRs, executive abstracts.</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-icon">🔍</span>
                <h3>EXTRACT</h3>
            </div>
            <div class="card-body">
                <p class="description">Isolating and retrieving specific data points from unstructured "haystacks."</p>
                <p class="example">Examples: Pulling dates from emails, entity recognition, data scraping.</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-icon">🔄</span>
                <h3>REFORMAT</h3>
            </div>
            <div class="card-body">
                <p class="description">Transforming the structure, language, or tone without changing the core meaning.</p>
                <p class="example">Examples: Translation, JSON to CSV, jargon-to-layman conversion.</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-icon">💡</span>
                <h3>GENERATE</h3>
            </div>
            <div class="card-body">
                <p class="description">Creating new content, concepts, or raw ideas from a prompt or seed idea.</p>
                <p class="example">Examples: Ideation, creative writing, drafting emails from scratch.</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="card-icon">🎭</span>
                <h3>SIMULATE</h3>
            </div>
            <div class="card-body">
                <p class="description">Modeling a persona, system, or scenario to predict or practice reactions.</p>
                <p class="example">Examples: Roleplaying difficult conversations, persona testing, scenario modeling.</p>
            </div>
        </div>

    </div>

    <footer>
        &copy; 2026 Tim Fraser. Prepared for Systems Engineering students.
    </footer>

</body>
</html>

