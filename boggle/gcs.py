from google.cloud import storage


def parse_gcs_path(gcs_path: str) -> tuple[str, str]:
    """Parses the GCS path into bucket name and prefix."""
    if not gcs_path.startswith("gs://"):
        raise ValueError("GCS path must start with 'gs://'")
    parts = gcs_path[5:].split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket_name, prefix


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
