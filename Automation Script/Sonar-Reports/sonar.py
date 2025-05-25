import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import argparse

def fetch_metrics(sonar_host, project_key, auth, headers):
    metric_keys = ",".join([
        "bugs", "vulnerabilities", "code_smells", "coverage",
        "duplicated_lines_density", "ncloc", "complexity", "reliability_rating",
        "security_rating", "sqale_rating", "lines", "functions", "classes"
    ])
    url = f"{sonar_host}/api/measures/component?component={project_key}&metricKeys={metric_keys}"
    return requests.get(url, auth=auth, headers=headers).json().get("component", {}).get("measures", [])

def fetch_project_info(sonar_host, project_key, auth, headers):
    url = f"{sonar_host}/api/projects/search?projects={project_key}"
    return requests.get(url, auth=auth, headers=headers).json().get("components", [{}])[0]

def fetch_quality_gate_status(sonar_host, project_key, auth, headers):
    url = f"{sonar_host}/api/qualitygates/project_status?projectKey={project_key}"
    return requests.get(url, auth=auth, headers=headers).json().get("projectStatus", {})

def fetch_issues(sonar_host, project_key, auth, headers):
    url = f"{sonar_host}/api/issues/search?componentKeys={project_key}&ps=1&p=1"
    initial = requests.get(url, auth=auth, headers=headers).json()
    total = initial.get("total", 0)
    page_size = 300
    total_pages = (total + page_size - 1) // page_size

    def get_page(page):
        url = f"{sonar_host}/api/issues/search?componentKeys={project_key}&ps={page_size}&p={page}"
        return requests.get(url, auth=auth, headers=headers).json().get("issues", [])

    with ThreadPoolExecutor() as executor:
        all_pages = list(executor.map(get_page, range(1, total_pages + 1)))

    return [item for sublist in all_pages for item in sublist]

def generate_charts(metrics, issues, charts_dir):
    os.makedirs(charts_dir, exist_ok=True)
    metric_dict = {
        m["metric"]: float(m["value"]) if m["value"].replace('.', '', 1).isdigit() else m["value"]
        for m in metrics
    }

    plt.bar(['bugs', 'vulnerabilities', 'code_smells'],
            [metric_dict.get(k, 0) for k in ['bugs', 'vulnerabilities', 'code_smells']],
            color='skyblue')
    plt.title('Code Quality Issues')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig(f"{charts_dir}/code_quality_issues.png")
    plt.close()

    issue_types = pd.Series([i['type'] for i in issues]).value_counts()
    issue_types.plot.pie(
        autopct='%1.1f%%',
        figsize=(6, 6),
        title='Issue Types Distribution',
        colors=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    )
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(f"{charts_dir}/issue_types.png")
    plt.close()

def generate_html(metrics, project, gate, issues, charts_dir, output_file):
    generate_charts(metrics, issues, charts_dir)

    issue_rows = ""
    for issue in issues:
        issue_rows += "<tr>"
        issue_rows += f"<td>{issue.get('key', '')}</td>"
        issue_rows += f"<td>{issue.get('severity', '')}</td>"
        issue_rows += f"<td>{issue.get('type', '')}</td>"
        issue_rows += f"<td>{issue.get('message', '').replace('<', '&lt;').replace('>', '&gt;')}</td>"
        issue_rows += f"<td>{issue.get('component', '')}</td>"
        issue_rows += f"<td>{issue.get('line', '') if issue.get('line') else '-'}</td>"
        issue_rows += f"<td>{issue.get('status', '')}</td>"
        issue_rows += "</tr>"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>SonarQube Report - {project.get('key')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f9f9f9;
                color: #333;
                margin: 20px;
                line-height: 1.6;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 2px solid #2980b9;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #34495e;
                margin-top: 40px;
                border-bottom: 1px solid #bdc3c7;
                padding-bottom: 5px;
            }}
            ul {{
                list-style-type: none;
                padding-left: 0;
            }}
            ul li {{
                padding: 4px 0;
                font-size: 1.1em;
            }}
            .charts-container {{
                display: flex;
                flex-direction: row;
                gap: 40px;
                margin-top: 20px;
                justify-content: space-between;
                flex-wrap: wrap;
            }}
            .charts-container img {{
                flex: 1;
                max-width: 48%;
                height: auto;
                border: 1px solid #ddd;
                border-radius: 5px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }}
            table {{
                border-collapse: separate;
                border-spacing: 0 8px;
                width: 100%;
                margin-top: 30px;
                background-color: #fff;
                table-layout: fixed;
            }}
            colgroup col:nth-child(1) {{ width: 12%; }}
            colgroup col:nth-child(2) {{ width: 10%; }}
            colgroup col:nth-child(3) {{ width: 10%; }}
            colgroup col:nth-child(4) {{ width: 30%; }}
            colgroup col:nth-child(5) {{ width: 20%; }}
            colgroup col:nth-child(6) {{ width: 8%; }}
            colgroup col:nth-child(7) {{ width: 10%; }}
            th, td {{
                text-align: left;
                padding: 16px 20px;
                border: 1px solid #ccc;
                font-size: 1em;
                vertical-align: top;
                word-wrap: break-word;
                white-space: normal;
            }}
            th {{
                background-color: #2980b9;
                color: white;
                letter-spacing: 0.03em;
                text-transform: uppercase;
                font-weight: 600;
            }}
            tr:hover {{
                background-color: #f1f8ff;
            }}
            @media (max-width: 768px) {{
                .charts-container {{
                    flex-direction: column;
                }}
                .charts-container img {{
                    max-width: 100%;
                }}
                th, td {{
                    padding: 12px 14px;
                    font-size: 0.95em;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>SonarQube Report - {project.get('key')}</h1>
        <p><b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>Metrics</h2>
        <ul>
            {''.join(f'<li>{m["metric"].replace("_", " ").title()}: {m["value"]}</li>' for m in metrics)}
        </ul>

        <h2>Quality Gate: <span style="color: {'green' if gate.get('status') == 'OK' else 'red'}; font-weight: 700;">{gate.get("status", "Unknown")}</span></h2>

        <div class="charts-container">
            <img src="{charts_dir}/code_quality_issues.png" alt="Code Quality Issues Chart" />
            <img src="{charts_dir}/issue_types.png" alt="Issue Types Distribution Chart" />
        </div>

        <h2>Issues ({len(issues)})</h2>
        <table>
            <colgroup>
                <col />
                <col />
                <col />
                <col />
                <col />
                <col />
                <col />
            </colgroup>
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Severity</th>
                    <th>Type</th>
                    <th>Message</th>
                    <th>Component</th>
                    <th>Line</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {issue_rows}
            </tbody>
        </table>
    </body>
    </html>
    """

    with open(output_file, "w", encoding='utf-8') as f:
        f.write(html_content)
    print(f"Report saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--charts-dir', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    auth = (args.token, "")
    headers = {"Accept": "application/json"}

    print("Fetching data from SonarQube...")
    with ThreadPoolExecutor() as executor:
        futures = {
            "metrics": executor.submit(fetch_metrics, args.host, args.project, auth, headers),
            "project": executor.submit(fetch_project_info, args.host, args.project, auth, headers),
            "gate": executor.submit(fetch_quality_gate_status, args.host, args.project, auth, headers),
            "issues": executor.submit(fetch_issues, args.host, args.project, auth, headers),
        }

        metrics = futures["metrics"].result()
        project = futures["project"].result()
        gate = futures["gate"].result()
        issues = futures["issues"].result()

    print("Generating HTML report...")
    generate_html(metrics, project, gate, issues, args.charts_dir, args.output)
