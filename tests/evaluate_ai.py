"""Manual synthetic-only preview/evaluation. Never imports application Settings/DB."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from pydantic import SecretStr
from app.services.ai_context import build, resolve, MAX_OUTPUT_BYTES
from app.services.ai_adapter import CommandProvider
from app.services.ai_execution import BoundedCall
from synthetic_ai_cases import synthetic_case


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['A','B'], default='A')
    parser.add_argument('--variant', choices=['normal','injection','empty','large'], default='normal')
    parser.add_argument('--adapter-script', type=Path)
    parser.add_argument('--run-reviewed-synthetic', action='store_true')
    args=parser.parse_args()
    try:
        context=build(synthetic_case(args.case,args.variant))
        print('SYNTHETIC ONLY: exact metadata payload follows; no files, credentials or database input.')
        print(context.data, flush=True)
        if not args.run_reviewed_synthetic:
            print('PREVIEW ONLY. No provider invoked.');return 0
        if args.adapter_script is None:
            print('No reviewed adapter configured.');return 2
        key=os.environ.get('SHADOWVAULT_AI_PROVIDER_API_KEY')
        if key and key in context.data:
            print('Synthetic payload rejected.');return 2
        provider=CommandProvider(args.adapter_script,SecretStr(key) if key else None)
        # Exactly one generation attempt per explicit command. No automatic retry.
        raw=asyncio.run(BoundedCall(provider,context.data,30,8000,MAX_OUTPUT_BYTES).run())
        sources=resolve(context,raw)
        print(json.dumps({'case':args.case,'resolved_citations':[s.citation for s in sources],
                          'status':'VALID_SELECTION_REQUIRES_HUMAN_REVIEW'}))
        return 0
    except Exception:
        print('Evaluation rejected, unavailable or timed out. No provider output published.');return 1

if __name__=='__main__':raise SystemExit(main())
