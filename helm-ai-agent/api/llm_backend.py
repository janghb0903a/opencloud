import os, json, textwrap, requests, boto3
from botocore.config import Config
import re, json

SYS_PROMPT = """You are a Helm Chart converter.

Return ONLY one valid JSON object:
{
  "chart_name": "string",
  "files": [{"path":"string","content":"string"}]
}

Hard rules:
- Output exactly one JSON object. No markdown, no code fences, no explanations.
- DO NOT invent resources not present in input. Only transform input objects.
- For EVERY input Kubernetes object, generate a corresponding template file under templates/ and parameterize to values.yaml when reasonable.
- Required top-level files: Chart.yaml, values.yaml, templates/_helpers.tpl
- Use {{ include "<chart>.fullname" . }} consistently for names/selectors.
- Escape quotes/newlines/backslashes inside "content".
- Keep Helm templates like {{ ... }} as raw text inside JSON strings (properly escaped).
"""

def build_user_prompt(chart_name: str, yaml_text: str, defaults: dict) -> str:
    return textwrap.dedent(f"""
    Convert the following Kubernetes manifests into a Helm chart named "{chart_name}".
    Merge these defaults into values.yaml if relevant:
    {json.dumps(defaults, ensure_ascii=False, indent=2)}

    Manifests:
    ---
    {yaml_text}
    """)

def call_bedrock(prompt: str):
    """
    Claude 3.5 Sonnet (Bedrock) 호출.
    - system 프롬프트는 top-level 'system'
    - messages[].role 은 'user'/'assistant'만 허용
    - 일부 리전/모델은 response_format 미지원 → 제거
    """
    import os, json, re
    import boto3
    from botocore.config import Config

    region = os.getenv("AWS_REGION", "ap-northeast-2")
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")

    br = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"max_attempts": 5, "mode": "standard"})
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.1,
        "system": SYS_PROMPT,   # ✅ 여기에 시스템 프롬프트
        "messages": [
            {
                "role": "user",
                "content": [ { "type": "text", "text": prompt } ]
            }
        ]
    }

    resp = br.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body).encode("utf-8")
    )

    payload = json.loads(resp["body"].read())
    text = "".join(c.get("text","") for c in payload.get("content",[]) if c.get("type")=="text").strip()

    def _coerce_json(t: str):
        t = re.sub(r"```(?:json)?|```", "", t, flags=re.I).strip()
        s = t.find("{"); e = t.rfind("}")
        if s != -1 and e != -1 and e > s:
            t = t[s:e+1]
        return json.loads(t)

    try:
        return json.loads(text)
    except Exception:
        return _coerce_json(text)

def call_llm(prompt: str):
    return call_bedrock(prompt)



