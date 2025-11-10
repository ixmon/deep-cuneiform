import gradio as gr
from openai import OpenAI
from PIL import Image
import io
import markdown

client = OpenAI(base_url='http://localhost:8000/v1', api_key='fake')  # Connect to local vLLM

def infer(image, is_finetuned):
    model = 'models/sumerian-deepseek-ocr' if is_finetuned else 'unsloth/DeepSeek-OCR'
    
    # Prepare image as base64 or bytes (vLLM/DeepSeek expects <image> token)
    buffered = io.BytesIO()
    image.save(buffered, format='JPEG')
    img_bytes = buffered.getvalue()

    prompt = '<image>\nExtract cuneiform signs as CDLI ATF transliteration format. Output only the ATF lines.'
    
    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': [{'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_bytes}'}}]}],
        max_tokens=1024
    )
    
    atf = response.choices[0].message.content.strip()
    
    # Optional markdown table: simple parse of ATF lines into table
    lines = atf.split('\n')
    table = '| Line | Signs |\n|------|-------|\n' + '\n'.join(f'| {i+1} | {line} |' for i, line in enumerate(lines) if line)
    md_table = markdown.markdown(table)
    
    return atf, md_table

with gr.Blocks() as demo:
    gr.Markdown('# Deep Cuneiform OCR Demo')
    image_input = gr.Image(type='pil', label='Upload Tablet Image')
    toggle = gr.Checkbox(label='Use Fine-Tuned Model (vs Zero-Shot)', value=False)
    atf_output = gr.Textbox(label='ATF Transliteration')
    table_output = gr.HTML(label='Signs Table (Optional)')
    submit = gr.Button('Transliterate')
    submit.click(infer, inputs=[image_input, toggle], outputs=[atf_output, table_output])

demo.launch(server_name='0.0.0.0', server_port=7860)
