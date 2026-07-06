#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch
from peft import PeftModel
from torch.utils.data import DataLoader
from transformers import AutoModelForVision2Seq, AutoProcessor

from scripts.granite_docling_lora_data import GraniteDoclingDataCollator, GraniteDoclingJsonlDataset


def move_batch(batch, device):
    return {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in batch.items()}


def first_diff(a: str, b: str) -> dict:
    if a == b:
        return {"match": True}
    limit = min(len(a), len(b))
    idx = next((i for i in range(limit) if a[i] != b[i]), limit)
    return {
        "match": False,
        "char_index": idx,
        "expected_slice": a[max(0, idx-80):idx+160],
        "generated_slice": b[max(0, idx-80):idx+160],
    }


def teacher_forced_accuracy(model, loader, device):
    rows=[]
    model.eval()
    with torch.no_grad():
        for batch in loader:
            image_id=batch['image_ids'][0]
            batch=move_batch(batch,device)
            out=model(
                input_ids=batch['input_ids'], attention_mask=batch['attention_mask'],
                pixel_values=batch.get('pixel_values'), pixel_attention_mask=batch.get('pixel_attention_mask'),
                labels=batch['labels']
            )
            logits=out.logits
            labels=batch['labels']
            shifted_logits=logits[:, :-1, :]
            shifted_labels=labels[:, 1:]
            mask=shifted_labels != -100
            pred=shifted_logits.argmax(dim=-1)
            correct=((pred == shifted_labels) & mask).sum().item()
            total=mask.sum().item()
            rows.append({'image_id': image_id, 'correct': correct, 'total': total, 'accuracy': correct/total if total else 0.0, 'loss': float(out.loss.item())})
    return rows


def generate_rows(model, dataset, processor, device, max_new_tokens, adapter_name):
    rows=[]
    model.eval()
    eos_text=processor.tokenizer.eos_token
    with torch.no_grad():
        for item in dataset:
            image_id=item['image_id']
            image = __import__('PIL').Image.open(item['image_path']).convert('RGB')
            inputs=processor(text=[item['prompt_text']], images=[image], return_tensors='pt', padding=False).to(device)
            out=model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
            prompt_len=inputs.input_ids.shape[1]
            gen_ids=out[0, prompt_len:]
            gen=processor.decode(gen_ids.tolist(), skip_special_tokens=False).lstrip()
            expected=item['target_text']
            terminated=eos_text in gen
            if terminated:
                # Keep through first EOS for exact target comparison.
                eos_end=gen.index(eos_text)+len(eos_text)
                comparable=gen[:eos_end]
            else:
                comparable=gen
            rows.append({
                'image_id': image_id,
                'adapter': adapter_name,
                'exact_match': comparable == expected,
                'terminated': terminated,
                'generated_tokens': int(gen_ids.numel()),
                'max_new_tokens': max_new_tokens,
                'diff': first_diff(expected, comparable),
                'generated_prefix': comparable[:500],
                'generated_suffix': comparable[-300:],
            })
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data-jsonl', type=Path, default=Path('data/train_26.jsonl'))
    ap.add_argument('--model-dir', type=Path, default=Path('model/ibm-granite/granite-docling-258M'))
    ap.add_argument('--adapter-dir', type=Path, default=Path('runs/overfit_26/adapter'))
    ap.add_argument('--output-json', type=Path, default=Path('runs/overfit_26/eval_overfit.json'))
    ap.add_argument('--max-length', type=int, default=8192)
    ap.add_argument('--max-new-tokens', type=int, default=6000)
    args=ap.parse_args()
    device='cuda' if torch.cuda.is_available() else 'cpu'
    dtype=torch.bfloat16 if device=='cuda' else torch.float32
    processor=AutoProcessor.from_pretrained(args.model_dir)
    processor.tokenizer.padding_side='left'
    dataset=GraniteDoclingJsonlDataset(args.data_jsonl, processor, max_length=args.max_length)
    loader=DataLoader(dataset,batch_size=1,shuffle=False,collate_fn=GraniteDoclingDataCollator(processor),num_workers=0)
    base=AutoModelForVision2Seq.from_pretrained(args.model_dir,dtype=dtype,_attn_implementation='sdpa').to(device)
    model=PeftModel.from_pretrained(base,args.adapter_dir).to(device)
    tf=teacher_forced_accuracy(model, loader, device)
    trained_gen=generate_rows(model, dataset, processor, device, args.max_new_tokens, 'trained')
    with model.disable_adapter():
        base_gen=generate_rows(model, dataset, processor, device, args.max_new_tokens, 'base_disabled')
    result={
        'teacher_forced': tf,
        'trained_generation': trained_gen,
        'base_generation': base_gen,
        'summary': {
            'teacher_forced_min_accuracy': min(r['accuracy'] for r in tf),
            'teacher_forced_all_100': all(r['accuracy'] >= 0.999 for r in tf),
            'trained_exact': sum(r['exact_match'] for r in trained_gen),
            'trained_terminated': sum(r['terminated'] for r in trained_gen),
            'base_exact': sum(r['exact_match'] for r in base_gen),
            'count': len(dataset),
        }
    }
    args.output_json.parent.mkdir(parents=True,exist_ok=True)
    args.output_json.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('EVAL_SUMMARY='+json.dumps(result['summary'],ensure_ascii=False,sort_keys=True))

if __name__ == '__main__':
    main()
