import json
import os
from tqdm import tqdm
from datasets import load_dataset
from utils import predict_gpt, predict_llama
import re
import argparse
from data_preprocessing import process_mmlu_questions, process_mmlu_pro_questions, load_aqua_questions, process_aqua_questions, load_gaokao_questions, process_gaokao_questions
from dotenv import load_dotenv
import openai
import anthropic
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login


load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')
login(token=os.getenv('HUGGING_FACE_HUB_TOKEN'))
anthropic_client = anthropic.Client(api_key=os.getenv('CLAUDE_API_KEY'))

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def main():
    parser = argparse.ArgumentParser(description="Process MMLU, MMLU-Pro, AQUA, or GaoKao questions")
    parser.add_argument("--dataset", choices=["mmlu", "mmlu-pro", "aqua", "gaokao"], required=True, help="Choose the dataset: 'mmlu', 'mmlu-pro', 'aqua', or 'gaokao'")
    parser.add_argument("--method", choices=["cot", "non-cot", "symbolicot"], required=True, help="Choose the method: 'cot', 'non-cot', or 'symbolicot'")
    parser.add_argument("--model", choices=["gpt", "llama"], required=True, help="Choose the model: 'gpt' or 'llama'")
    args = parser.parse_args()

    output_dir = f"results/{args.dataset}/{args.method}/{args.model}"
    output_file_path = f"{output_dir}/{args.method}_{args.model}.json"

    if args.dataset == "mmlu":
        prompt_dir = 'prompts/MMLU-Mathematics'
    elif args.dataset == "mmlu-pro":
        prompt_dir = 'prompts/MMLU-Pro-Mathematics'
    elif args.dataset == "aqua":
        prompt_dir = 'prompts/AQUA-Mathematics'
    else:  # gaokao
        prompt_dir = 'prompts/GaoKao-Math'

    formulation_prompt_path = f"{prompt_dir}/{args.method}.txt"

    # Ensure the directory exists
    ensure_dir(output_file_path)

    # Create the output file
    with open(output_file_path, 'w') as f:
        json.dump([], f)
    print(f"Created output file: {output_file_path}")

    if args.model == "gpt":
        model = openai
        tokenizer = None
        device = None
    else:  # llama
        model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
        tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            use_auth_token=True,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True
        )

    if args.dataset == "mmlu":
        # Load MMLU dataset
        dataset = load_dataset("cais/mmlu", "college_mathematics", split="test")
        results, accuracy = process_mmlu_questions(dataset, output_file_path, formulation_prompt_path, model, tokenizer, args.model)
    elif args.dataset == "mmlu-pro":
        # Load MMLU-Pro dataset
        dataset = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
        math_dataset = dataset.filter(lambda example: example['category'] == 'math')
        results, accuracy = process_mmlu_pro_questions(math_dataset, output_file_path, formulation_prompt_path, model, tokenizer, args.model)
    elif args.dataset == "aqua":
        # Load AQUA dataset
        questions = load_aqua_questions('prompts/AQUA-Mathematics/test.json')
        results, accuracy = process_aqua_questions(questions, output_file_path, formulation_prompt_path, model, tokenizer, args.model)
    else:  # gaokao
        # Load GaoKao dataset
        questions = load_gaokao_questions('prompts/GaoKao-Math/2023_Math_MCQs.json')
        results, accuracy = process_gaokao_questions(questions, output_file_path, formulation_prompt_path, model, tokenizer, args.model)

    print(results)
    print(f"Final results saved to {output_file_path}")
    print(f"Final Accuracy: {accuracy:.2%}")

if __name__ == "__main__":
    main()