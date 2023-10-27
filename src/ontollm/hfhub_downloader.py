#!/usr/bin/env python
import sys
import argparse
from huggingface_hub import snapshot_download
from is_safe_url import is_safe_url

def main():
    parser = argparse.ArgumentParser(description = 'Downloads repo snapshot from Hugging Face Hub')
    parser.add_argument('repo_id', help="identifier of the repo to download")
    parser.add_argument('-r', '--revision', default='main',
                        help="revision of the repo to download")
    args = parser.parse_args()

    # Safety check
    raw_url = "https://huggingface.co/" + args.repo_id + "/tree/" + args.revision
    if not is_safe_url(raw_url, allowed_hosts={"huggingface.co"}):
        _ = sys.stderr.write(
                "Could not verify safety of the proposed url; exiting...\n")
        sys.exit(1)

    print("Please enter your HuggingFace token. ")
    hf_token = input()

    try:
        local_snapshot_path = snapshot_download(args.repo_id, 
                                                revision=args.revision,
                                                token=hf_token)
    except ValueError:
        _ = sys.stderr.write(
            "An invalid parameter was submitted to snapshot_download(). Exiting...\n")
        sys.exit(1)
    except OSError:
        _ = sys.stderr.write("ETag could not be determined. Exiting...\n")
        sys.exit(1)

    print(f"Downloaded snapshot of {args.repo_id} revision {args.revision} to {local_snapshot_path}")


if __name__ == '__main__':
    main()
