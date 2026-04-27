import torch
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import json
import os

# Принудительно используем CPU (обход ошибки MPS)
os.environ["CUDA_VISIBLE_DEVICES"] = ""
device = torch.device("cpu")

print("=" * 60)
print("ВАЛИДАЦИЯ ТРЁХ МОДЕЛЕЙ (CPU)")
print("=" * 60)

test_df = pd.read_csv("data/finetuning/test.csv")
print(f"Загружено {len(test_df)} тестовых примеров")

def format_input(text):
    return f"Оригинал: {text}\nУпрощённо:"

models = [
    {
        "name": "TinyLlama",
        "base_model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "adapter_path": "data/finetuning/lora_tinyllama"
    },
    {
        "name": "OPT-350m",
        "base_model": "facebook/opt-350m",
        "adapter_path": "data/finetuning/lora_opt_350m"
    },
    {
        "name": "GPT-2",
        "base_model": "gpt2",
        "adapter_path": "data/finetuning/lora_gpt2"
    }
]

results = {}

for model_info in models:
    print("\n" + "=" * 60)
    print(f"ВАЛИДАЦИЯ: {model_info['name']}")
    print("=" * 60)
    
    tokenizer = AutoTokenizer.from_pretrained(model_info["base_model"])
    tokenizer.pad_token = tokenizer.eos_token
    
    print("Загрузка базовой модели (CPU)...")
    base_model = AutoModelForCausalLM.from_pretrained(
        model_info["base_model"],
        torch_dtype=torch.float32,
    ).to(device)
    
    print("Загрузка адаптера...")
    model = PeftModel.from_pretrained(base_model, model_info["adapter_path"])
    model.to(device)
    model.eval()
    
    correct = 0
    total = min(10, len(test_df))
    
    for i, row in test_df.head(total).iterrows():
        input_text = row["input"]
        expected = row["output"]
        
        prompt = format_input(input_text)
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.7,
                do_sample=True,
            )
        
        prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)
        if "Упрощённо:" in prediction:
            prediction = prediction.split("Упрощённо:")[-1].strip()
        elif "Simplified:" in prediction:
            prediction = prediction.split("Simplified:")[-1].strip()
        
        if expected.lower() in prediction.lower() or prediction.lower() in expected.lower():
            correct += 1
            print(f"  OK {i+1}/{total}")
        else:
            print(f"  FAIL {i+1}/{total}")
    
    accuracy = correct / total
    results[model_info["name"]] = {"accuracy": accuracy, "correct": correct, "total": total}
    
    print(f"\nТочность на {total} примерах: {accuracy:.1%}")
    print(f"Правильных ответов: {correct}/{total}")

with open("data/finetuning/validation_results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 60)
print("ИТОГОВАЯ ТАБЛИЦА")
print("=" * 60)
for name, res in results.items():
    print(f"{name}: {res['accuracy']:.1%} ({res['correct']}/{res['total']})")