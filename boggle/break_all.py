#!/usr/bin/env python

import argparse
import atexit
import glob
import itertools
import json
import math
import multiprocessing
import os
import random
import time
from dataclasses import dataclass

from google.cloud import storage
from tqdm import tqdm

from boggle.args import (
    add_standard_args,
    get_trie_and_boggler_from_args,
)
from boggle.board_id import from_board_id, is_canonical_board_id, parse_classes
from boggle.boggler import PyBoggler
from boggle.breaker import HybridTreeBreaker
from boggle.dimensional_bogglers import (
    cpp_bucket_boggler,
    cpp_orderly_tree_builder,
)
from boggle.ibucket_breaker import IBucketBreaker
from boggle.ibuckets import PyBucketBoggler
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import PyTrie


@dataclass
class BreakingBundle:
    """Only the breaker is needed, but this helps keep its deps from being GC'd."""

    trie: PyTrie
    boggler: PyBoggler
    etb: OrderlyTreeBuilder
    breaker: IBucketBreaker | HybridTreeBreaker


def get_process_id():
    ids = multiprocessing.current_process()._identity
    if len(ids) == 0:
        return 1  # single-threaded case
    assert len(ids) == 1
    return ids[0]


# Global variable to track the last upload time
last_upload_time_secs = None

MAX_GCS_UPLOAD_FREQUENCY_SECS = 60 * 10


def break_init(args, needs_canonical_filter):
    global last_upload_time_secs
    bundle = get_breaker(args)
    # See https://stackoverflow.com/a/30816116/388951 for this trick to avoid a global
    break_worker.bundle = bundle
    break_worker.args = args
    break_worker.needs_canonical_filter = needs_canonical_filter
    me = get_process_id()
    with open(f"{args.output_base}-{me}.ndjson", "w"):
        pass
    last_upload_time_secs = time.time()
    atexit.register(final_sync)


def upload_to_gcs(source_file_name: str, gcs_path: str):
    """Uploads a file to the Google Cloud Storage bucket."""
    gcs_bucket, gcs_prefix = parse_gcs_path(gcs_path)
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blob = bucket.blob(gcs_prefix)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {gcs_path}.")


def download_from_gcs(gcs_path: str, local_dir: str):
    """Downloads files from the Google Cloud Storage bucket."""
    gcs_bucket, gcs_prefix = parse_gcs_path(gcs_path)
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket)
    blobs = bucket.list_blobs(prefix=gcs_prefix)
    for blob in blobs:
        local_path = f"{local_dir}/{os.path.basename(blob.name)}"
        blob.download_to_filename(local_path)
        print(f"File {blob.name} downloaded to {local_path}.")


def final_sync():
    args = break_worker.args
    me = get_process_id()
    if args.gcs_path:
        print(f"Performing final sync to GCS for process {me}")
        upload_to_gcs(
            f"{args.output_base}-{me}.ndjson",
            f"{args.gcs_path}/{args.timestamp}.tasks-{me}.ndjson",
        )


def break_worker(task: str | int):
    global last_upload_time_secs
    bundle: BreakingBundle = break_worker.bundle
    breaker = bundle.breaker
    args = break_worker.args
    needs_canonical_filter = break_worker.needs_canonical_filter
    me = get_process_id()

    best_score = args.best_score
    assert best_score > 0
    dims = args.size // 10, args.size % 10
    classes = parse_classes(args.classes, dims)

    if isinstance(task, int):
        if needs_canonical_filter and not is_canonical_board_id(
            [len(c) for c in classes], dims, task
        ):
            return []
        board = from_board_id(classes, task)
        if args.log_breaker_progress:
            print(f"{me} Starting {task}: {board}")
    else:
        board = task
        if args.log_breaker_progress:
            print(f"{me} Starting {task}")

    assert breaker.SetBoard(board)
    details = breaker.Break()
    if details.failures:
        for failure in details.failures:
            print(f"Found unbreakable board for {task}: {failure}")
        # good_boards += details.failures
    # depths[details.max_depth] += 1
    # times[round(10 * details.elapsed_s) / 10] += 1
    # all_details.append((task, details))
    with open(f"{args.output_base}-{me}.ndjson", "a") as out:
        # It's convenient to have id first when viewing.
        summary = {"id": task, **details.asdict()}
        if args.omit_times:
            del summary["elapsed_s"]
            del summary["secs_by_level"]
            del summary["test_secs"]
            del summary["bound_secs"]
        out.write(json.dumps(summary))
        out.write("\n")
        if args.log_per_board_stats:
            print(f"{task}: {board}")
            print(json.dumps(summary, indent=2))

    # Upload the file to Google Cloud Storage if 10 minutes have passed
    current_time_secs = time.time()
    if (
        args.gcs_path
        and current_time_secs - last_upload_time_secs >= MAX_GCS_UPLOAD_FREQUENCY_SECS
    ):
        upload_to_gcs(
            f"{args.output_base}-{me}.ndjson",
            f"{args.gcs_path}/{args.timestamp}.tasks-{me}.ndjson",
        )
        last_upload_time_secs = current_time_secs

    return details.failures


def get_breaker(args) -> BreakingBundle:
    """Each thread needs its own Trie, tree builder, boggler and breaker."""
    dims = args.size // 10, args.size % 10
    best_score = args.best_score

    t, boggler = get_trie_and_boggler_from_args(args)

    builder = OrderlyTreeBuilder if args.python else cpp_orderly_tree_builder
    etb = builder(t, dims)

    if args.breaker == "hybrid":
        switchover_score = args.switchover_score or 2.5 * best_score
        breaker = HybridTreeBreaker(
            etb,
            boggler,
            dims,
            best_score,
            switchover_score=switchover_score,
            log_breaker_progress=args.log_breaker_progress,
        )
    elif args.breaker == "ibuckets":
        etb = (PyBucketBoggler if args.python else cpp_bucket_boggler)(t, dims)
        breaker = IBucketBreaker(
            etb,
            dims,
            best_score,
            num_splits=args.num_splits,
            log_breaker_progress=args.log_breaker_progress,
        )
    else:
        raise ValueError(args.breaker)
    return BreakingBundle(trie=t, etb=etb, boggler=boggler, breaker=breaker)


def parse_gcs_path(gcs_path: str) -> tuple[str, str]:
    """Parses the GCS path into bucket name and prefix."""
    if not gcs_path.startswith("gs://"):
        raise ValueError("GCS path must start with 'gs://'")
    parts = gcs_path[5:].split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket_name, prefix


def main():
    parser = argparse.ArgumentParser(
        description="Find all MxN boggle boards with >=P points",
    )
    parser.add_argument(
        "classes", type=str, help="Space-separated list of letter classes"
    )
    parser.add_argument(
        "best_score",
        type=int,
        help="Print boards with a score >= to this. Filter boards below this. "
        "A higher number will result in a faster run.",
    )
    add_standard_args(parser, random_seed=True, python=True)
    parser.add_argument(
        "--board_ids",
        help="Comma-separated list of board IDs. Omit to consider all "
        "canonically-rotated boards.",
    )
    parser.add_argument(
        "--max_boards",
        help="Limit the number of boards to consider.",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--num_splits",
        type=int,
        default=4,
        help="Number of partitions to use when breaking a bucket. Only relevant with --breaker=ibuckets.",
    )
    parser.add_argument(
        "--switchover_score",
        type=int,
        default=None,
        help="When to switch from splitting the tree by forcing cells to evaluating the "
        "remaining tree with a DFS. Higher values will use less RAM but potentially run "
        "more slowly. The default is 2.5 * best_score.",
    )
    parser.add_argument(
        "--breaker",
        type=str,
        choices=("ibuckets", "hybrid"),
        default="hybrid",
        help="Breaking strategy to use.",
    )
    parser.add_argument(
        "--break_class",
        type=str,
        help="Set to a board class to override --random_ids, --max_boards, etc.",
    )
    parser.add_argument(
        "--num_threads",
        type=int,
        default=1,
        help="Number of concurrent breakers to run.",
    )
    parser.add_argument(
        "--resume_from",
        type=str,
        help="Glob pattern of ndjson output files from a previous run.",
    )
    parser.add_argument(
        "--log_per_board_stats",
        action="store_true",
        help="Log stats on every board to stdout, rather just to an ndjson file.",
    )
    parser.add_argument(
        "--log_breaker_progress",
        action="store_true",
        help="Log progress and stats during breaking, which may slow it down.",
    )
    parser.add_argument(
        "--omit_times",
        action="store_true",
        help="Omit times from logging, to get deterministic output.",
    )
    parser.add_argument(
        "--output_base",
        default="tasks",
        help="Outputs will be written to output_base-thread_id.ndjson.",
    )
    parser.add_argument(
        "--gcs_path",
        type=str,
        help="Google Cloud Storage path to upload the results, e.g., 'gs://bucket/path'.",
    )
    args = parser.parse_args()
    if args.random_seed >= 0:
        random.seed(args.random_seed)

    # Generate a timestamp for the current run
    args.timestamp = time.strftime("%Y%m%d-%H%M%S")

    # Download existing files from GCS bucket if gcs_path is provided
    if args.gcs_path:
        assert not args.resume_from
        local_resume_dir = "/tmp/resume_files"
        os.makedirs(local_resume_dir, exist_ok=True)
        download_from_gcs(args.gcs_path, local_resume_dir)
        args.resume_from = f"{local_resume_dir}/*"

    best_score = args.best_score
    assert best_score > 0
    w, h = dims = args.size // 10, args.size % 10
    assert 3 <= w <= 5
    assert 3 <= h <= 5
    classes = parse_classes(args.classes, dims)
    assert len(classes) == w * h
    num_classes = [len(c) for c in classes]
    max_index = math.prod(num_classes)

    completed_ids = set()
    if args.resume_from:
        n_files = 0
        for filename in glob.glob(args.resume_from):
            n_files += 1
            with open(filename) as input:
                for line in input:
                    task = json.loads(line)
                    completed_ids.add(task["id"])
        print(f"Recovered {len(completed_ids)} completed IDs from {n_files} files.")

    indices: list[int | str]
    needs_canonical_filter = False
    if args.board_ids:
        indices = [int(x) for x in args.board_ids.split(",")]
    elif args.break_class:
        break_class = args.break_class
        assert len(break_class.split(" ")) == w * h
        indices = [break_class]
    else:
        # This gets a more useful, accurate error bar than going in order
        # and filtering inside the main loop.
        start_s = time.time()
        if args.max_boards:
            # This is dramatically faster than slicing the full permutation array.
            oversample = random.sample(range(max_index), k=16 * args.max_boards)
            indices = (
                idx
                for idx in oversample
                if is_canonical_board_id(num_classes, dims, idx)
            )
            indices = [*itertools.islice(indices, args.max_boards)]
        else:
            indices = [
                idx
                for idx in range(0, max_index)
                # if is_canonical_board_id(num_classes, dims, idx)
            ]
            random.shuffle(indices)
            # Filtering on the workers results in faster startup.
            needs_canonical_filter = True
        indices = [idx for idx in indices if idx not in completed_ids]
        boards_type = "total" if needs_canonical_filter else "canonical"
        print(
            f"Found {len(indices)} {boards_type} boards in {time.time() - start_s:.02f}s."
        )

    start_s = time.time()
    good_boards = []

    pool = None
    if args.num_threads > 1:
        pool = multiprocessing.Pool(
            args.num_threads, break_init, (args, needs_canonical_filter)
        )
        it = pool.imap_unordered(break_worker, indices)
    else:
        # This keeps stack traces simpler in the single-threaded case.
        break_init(args, needs_canonical_filter)
        it = (break_worker(task) for task in indices)

    good_boards = []
    # smoothing=0 means to show the average pace so far, which is the best estimator.
    for winners in tqdm(it, smoothing=0, total=len(indices)):
        good_boards.extend(winners)

    end_s = time.time()

    if not args.omit_times:
        print(f"Broke {len(indices)} classes in {end_s-start_s:.02f}s.")
    print(f"Found {len(good_boards)} breaking failure(s):")
    print("\n".join(good_boards))

    if pool:
        pool.close()
        pool.join()


if __name__ == "__main__":
    main()
