#!/bin/bash

directories=("./data/jsonls/joined_jsonls_clean.jsonl"
"./data/jsonls/joined_jsonls.jsonl"
"./data/jsonls/eval_instances_tulu_1.jsonl"
"./data/jsonls/llama3_alpaca_4_2048_5e-7_persian_system_prompt_vs_llama3_alpaca_4_2048_persian_system_prompt.jsonl"
"./data/jsonls/llama3_alpaca_4_2048_5e-7_persian_system_prompt_vs_Part V1.jsonl"
"./data/jsonls/llama3_alpaca_4_2048_persian_system_prompt_vs_Part V1.jsonl"
"./data/jsonls/llama3_alpaca_4_2048_vs_llama3_base.jsonl"
"./data/jsonls/llama3_alpaca_4_2048_vs_Part V1.jsonl"
"./data/jsonls/llama3_base_persian_system_prompt_vs_llama3_alpaca_4_2048_5e-7_persian_system_prompt.jsonl"
"./data/jsonls/llama3_base_persian_system_prompt_vs_llama3_alpaca_4_2048_persian_system_prompt.jsonl"
"./data/jsonls/llama3_base_persian_system_prompt_vs_llama3_base.jsonl"
"./data/jsonls/llama3_base_persian_system_prompt_vs_Part V1.jsonl"
"./data/jsonls/llama3_base_vs_Part V1.jsonl"
"./data/jsonls/llama3_alpaca_4_2048_5e-7_persian_system_prompt_vs_llama3_alpaca_clean_4_2048_persian_system_prompt.jsonl")


directory_index=0
port=5001

while getopts "p:d:" opt; do
  case $opt in
    p) port="$OPTARG"
    ;;
    d) directory_index="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    ;;
  esac
done

directory=${directories[$directory_index]}

echo "[directory_index: $directory_index, directory: $directory, port: $port]"


python app.py --comparison_data_path "${directory}" --port $port

# ./run.sh -d 0 -p 5001

# 1 6 8
