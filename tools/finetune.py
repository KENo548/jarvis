#!/usr/bin/env python3
"""
JARVIS LLM Fine-Tuning Script
Uses LoRA/QLoRA to fine-tune Llama 3.2 for JARVIS-specific tasks.
"""

import os
import json
import torch
from pathlib import Path

# Configuration
BASE_MODEL = "meta-llama/Llama-3.2-1B"  # Use 1B for local fine-tuning
OUTPUT_DIR = Path(__file__).parent.parent / "models" / "jarvis-finetuned"
DATA_DIR = Path(__file__).parent.parent / "data"

def create_training_data():
    """Create JARVIS-specific training data."""
    DATA_DIR.mkdir(exist_ok=True)
    
    training_examples = [
        # System prompts
        {
            "instruction": "You are JARVIS, an AI assistant created by Tony Stark.",
            "input": "What is your purpose?",
            "output": "I am JARVIS, an advanced AI assistant designed to help with research, analysis, coding, and automation tasks. I follow the Iron Law: never act without user confirmation on state-changing operations."
        },
        {
            "instruction": "Respond as JARVIS would.",
            "input": "What can you do?",
            "output": "I can help with software engineering, research, data analysis, content creation, and system administration. I have access to tools for web search, code execution, file management, and more."
        },
        # Research tasks
        {
            "instruction": "Research and summarize the following topic.",
            "input": "Explain quantum computing in simple terms.",
            "output": "Quantum computing uses quantum bits (qubits) that can exist in multiple states simultaneously, unlike classical bits which are either 0 or 1. This allows quantum computers to solve certain problems exponentially faster than classical computers."
        },
        # Code generation
        {
            "instruction": "Write a Python function to calculate factorial.",
            "input": "Write a factorial function",
            "output": "```python\ndef factorial(n):\n    if n < 0:\n        raise ValueError('Factorial not defined for negative numbers')\n    if n == 0 or n == 1:\n        return 1\n    return n * factorial(n - 1)\n```"
        },
        # Task planning
        {
            "instruction": "Break down this task into steps.",
            "input": "Deploy a web application to production",
            "output": "1. Run tests to ensure code quality\n2. Build production artifacts\n3. Update dependencies\n4. Configure environment variables\n5. Deploy to staging environment\n6. Run integration tests\n7. Deploy to production\n8. Monitor for errors"
        },
        # Security
        {
            "instruction": "Analyze this code for security vulnerabilities.",
            "input": "```python\nquery = request.args.get('q')\ncursor.execute(f\"SELECT * FROM users WHERE name='{query}'\")\n```",
            "output": "SQL Injection vulnerability detected. The query directly interpolates user input into SQL. Use parameterized queries instead: cursor.execute('SELECT * FROM users WHERE name=%s', (query,))"
        },
        # Data analysis
        {
            "instruction": "Analyze this dataset and provide insights.",
            "input": "Sales data: Q1=100, Q2=150, Q3=120, Q4=200",
            "output": "Analysis: Total sales = 570 units. Q4 showed strongest performance (+67% from Q3). Overall trend is upward despite Q3 dip. Recommend investigating Q3 factors and capitalizing on Q4 momentum."
        },
    ]
    
    # Save as JSONL
    output_path = DATA_DIR / "jarvis_training.jsonl"
    with open(output_path, "w") as f:
        for example in training_examples:
            f.write(json.dumps(example) + "\n")
    
    print(f"[OK] Created {len(training_examples)} training examples at {output_path}")
    return output_path


def setup_lora_config():
    """Configure LoRA for efficient fine-tuning."""
    from peft import LoraConfig, get_peft_model, TaskType
    
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,  # LoRA rank
        lora_alpha=32,  # Alpha scaling
        lora_dropout=0.1,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )
    
    print("[OK] LoRA config created")
    print(f"  Rank: {lora_config.r}")
    print(f"  Alpha: {lora_config.lora_alpha}")
    print(f"  Target modules: {lora_config.target_modules}")
    
    return lora_config


def load_model():
    """Load base model with quantization for memory efficiency."""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    
    print(f"[*] Loading base model: {BASE_MODEL}")
    
    # 4-bit quantization for memory efficiency
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
    )
    
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
    )
    
    print(f"[OK] Model loaded: {model.num_parameters()} parameters")
    return model, tokenizer


def prepare_dataset(tokenizer, data_path):
    """Prepare dataset for training."""
    from datasets import load_dataset
    
    dataset = load_dataset("json", data_files=str(data_path))
    
    def format_prompt(example):
        instruction = example["instruction"]
        inp = example.get("input", "")
        output = example["output"]
        
        if inp:
            prompt = f"<|system|>\n{instruction}\n<|user|>\n{inp}\n<|assistant|>\n{output}"
        else:
            prompt = f"<|system|>\n{instruction}\n<|assistant|>\n{output}"
        
        return {"text": prompt}
    
    dataset = dataset.map(format_prompt)
    print(f"[OK] Dataset prepared: {len(dataset['train'])} examples")
    return dataset


def train():
    """Run fine-tuning."""
    from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
    from peft import get_peft_model
    
    # Create training data
    data_path = create_training_data()
    
    # Load model and tokenizer
    model, tokenizer = load_model()
    
    # Setup LoRA
    lora_config = setup_lora_config()
    model = get_peft_model(model, lora_config)
    
    # Prepare dataset
    dataset = prepare_dataset(tokenizer, data_path)
    
    # Training arguments
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        weight_decay=0.01,
        warmup_steps=10,
        logging_steps=5,
        save_steps=50,
        save_total_limit=2,
        fp16=True,
        report_to="none",
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        data_collator=data_collator,
    )
    
    # Train
    print("\n[*] Starting fine-tuning...")
    trainer.train()
    
    # Save
    print(f"\n[*] Saving model to {OUTPUT_DIR}")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # Create Ollama Modelfile
    modelfile = f"""
FROM {BASE_MODEL}

TEMPLATE \"\"\"{{{{ if .System }}}}<|system|>
{{{{ .System }}}}
{{{{ end }}}}<|user|>
{{{{ .Prompt }}}}
<|assistant|>
{{{{ .Response }}}}\"\"\"

SYSTEM \"You are JARVIS, an AI assistant created by Tony Stark.\"

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
"""
    
    modelfile_path = OUTPUT_DIR / "Modelfile"
    with open(modelfile_path, "w") as f:
        f.write(modelfile)
    
    print(f"\n[OK] Fine-tuning complete!")
    print(f"  Model saved to: {OUTPUT_DIR}")
    print(f"  Modelfile at: {modelfile_path}")
    print(f"\n  To use with Ollama:")
    print(f"    ollama create jarvis -f {modelfile_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS LLM Fine-Tuning")
    parser.add_argument("--create-data", action="store_true", help="Create training data only")
    parser.add_argument("--train", action="store_true", help="Run fine-tuning")
    args = parser.parse_args()
    
    if args.create_data:
        create_training_data()
    elif args.train:
        train()
    else:
        print("Usage:")
        print("  python finetune.py --create-data  # Create training data")
        print("  python finetune.py --train        # Run fine-tuning")
