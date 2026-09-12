import requests

BASE_URL = 'https://raw.githubusercontent.com/Alpha-Stochastic-Research/asr-quant/1c85a3386ce4cd826d3302d085e5aa76ad985b9d/dinav-qf-kaggle-cli/dinav_qf_125m_pilot.py'
response = requests.get(BASE_URL, timeout=60)
response.raise_for_status()
code = compile(response.text, BASE_URL, 'exec')
exec(code, {'__name__': '__main__', '__file__': BASE_URL})
