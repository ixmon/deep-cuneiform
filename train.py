# train.py — DeepSeek-OCR Cuneiform OCR Fine-Tuning (4090)
import os
import torch
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments, CLIPImageProcessor
from peft import LoraConfig, get_peft_model
from datasets import Dataset
from PIL import Image
import warnings

warnings.filterwarnings("ignore")

# ==============================
# 1. CONFIG
# ==============================
DATA_DIR = "data"
IMAGE_DIR = os.path.join(DATA_DIR, "images")
ANN_DIR = os.path.join(DATA_DIR, "annotations")
OUTPUT_DIR = "outputs"
FINAL_MODEL_DIR = "models/sumerian-deepseek-ocr"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FINAL_MODEL_DIR, exist_ok=True)

# ==============================
# 2. LOAD DATASET
# ==============================
image_paths = [
    os.path.join(IMAGE_DIR, f)
    for f in os.listdir(IMAGE_DIR)
    if f.lower().endswith(('.jpg', '.png', '.jpeg'))
]

atf_texts = []
for img_file in [os.path.basename(p) for p in image_paths]:
    base_name = os.path.splitext(img_file)[0]
    ann_path = os.path.join(ANN_DIR, f"{base_name}.atf")
    if os.path.exists(ann_path):
        with open(ann_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
    else:
        text = "# No annotation"
    atf_texts.append(text)

raw_dataset = Dataset.from_dict({"image": image_paths, "text": atf_texts})
dataset_split = raw_dataset.train_test_split(test_size=0.2, seed=3407)
train_dataset = dataset_split["train"]
eval_dataset = dataset_split["test"]

print(f"Loaded {len(train_dataset)} train, {len(eval_dataset)} eval samples.")

# ==============================
# 3. LOAD TOKENIZER & IMAGE PROCESSOR
# ==============================
tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-OCR", trust_remote_code=True)
tokenizer.padding_side = "left"

# Use CLIP image processor (DeepSeek-VL2 vision tower is CLIP-based)
image_processor = CLIPImageProcessor.from_pretrained("openai/clip-vit-large-patch14")

# ==============================
# 4. LOAD MODEL
# ==============================
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModel.from_pretrained(
    "deepseek-ai/DeepSeek-OCR",
    quantization_config=quantization_config,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)

# ==============================
# 5. LoRA
# ==============================
lora_config = LoraConfig(
    r=16,
    lora_alpha=16,
    target_modules=[
        'q_proj', 'k_proj', 'v_proj', 'o_proj',
        'gate_proj', 'up_proj', 'down_proj'
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ==============================
# 6. PREPROCESS FUNCTION (FIXED WITH PIL)
# ==============================
def preprocess_function(examples):
    image_paths = examples["image"]
    texts = examples["text"]
    prompt = "User: Transcribe this cuneiform tablet in ATF format.\n"
