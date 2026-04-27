import torch
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
from datasets import Dataset
import time
import json

print("Загрузка данных...")
df = pd.read_csv("data/finetuning/train.csv").head(500)
val_df = pd.read_csv("data/finetuning/val.csv").head(100)

def format_example(row):
    return f"Оригинал: {row['input']}\nУпрощённо: {row['output']}"

train_texts = [format_example(row) for _, row in df.iterrows()]
val_texts = [format_example(row) for _, row in val_df.iterrows()]

train_dataset = Dataset.from_dict({"text": train_texts})
val_dataset = Dataset.from_dict({"text": val_texts})

# ТРИ ПОЛНОСТЬЮ ОТКРЫТЫЕ МОДЕЛИ 
models = [
    {
        "name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "output_dir": "data/finetuning/lora_tinyllama",
        "target_modules": ["q_proj", "v_proj"]
    },
    {
        "name": "facebook/opt-350m",
        "output_dir": "data/finetuning/lora_opt_350m",
        "target_modules": ["q_proj", "v_proj"]
    },
    {
        "name": "gpt2",
        "output_dir": "data/finetuning/lora_gpt2",
        "target_modules": ["c_attn"] 
    }
]

results = {}

for model_config in models:
    model_name = model_config["name"]
    output_dir = model_config["output_dir"]
    target_modules = model_config["target_modules"]
    
    print("\n" + "=" * 60)
    print(f"ОБУЧЕНИЕ МОДЕЛИ: {model_name}")
    print("=" * 60)
    
    start_time = time.time()
    
    print("Загрузка токенизатора...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    
    def tokenize(examples):
        tokenized = tokenizer(
            examples["text"], 
            truncation=True, 
            padding="max_length", 
            max_length=256
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized
    
    tokenized_train = train_dataset.map(tokenize, batched=True)
    tokenized_val = val_dataset.map(tokenize, batched=True)
    
    print(f"Загрузка модели {model_name}...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype=torch.float32,
    )
    
    print("Настройка LoRA...")
    lora_config = LoraConfig(
        r=4,
        lora_alpha=8,
        target_modules=target_modules,
        lora_dropout=0.1,
    )
    model = get_peft_model(model, lora_config)
    
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Обучаемых параметров: {trainable:,} ({100*trainable/total:.2f}%)")
    
    print("Запуск обучения...")
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=2,
        num_train_epochs=1,
        eval_strategy="steps",
        eval_steps=50,
        logging_steps=20,
        save_steps=100,
        learning_rate=2e-4,
        report_to="none",
        dataloader_pin_memory=False,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_val,
    )
    
    trainer.train()
    
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    elapsed = time.time() - start_time
    results[model_name] = {"time_min": elapsed / 60, "output_dir": output_dir}
    
    print(f" {model_name} обучена за {elapsed/60:.1f} минут")

with open("data/finetuning/finetune_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 60)
print("ОБУЧЕНИЕ ТРЁХ МОДЕЛЕЙ ЗАВЕРШЕНО!")
print("=" * 60)
for model_name, res in results.items():
    print(f"{model_name}: {res['time_min']:.1f} мин → {res['output_dir']}")