"""
Data Source Connectors — All 16 Enterprise Sources
=====================================================
Each connector implements the BaseConnector interface for pulling
documents from external data sources.
"""

import uuid
import structlog
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from pathlib import Path
from datetime import datetime

logger = structlog.get_logger()


class BaseConnector(ABC):
    """Abstract base for all 16 data source connectors."""

    kind: str = ""
    category: str = ""
    icon: str = "📄"
    description: str = ""
    supported_extensions: List[str] = []
    requires_oauth: bool = False
    requires_api_key: bool = False

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection. Returns True on success."""
        ...

    @abstractmethod
    async def list_documents(self) -> List[Dict[str, Any]]:
        """List available documents from the source."""
        ...

    @abstractmethod
    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        """Download a document to dest_path. Returns local file path."""
        ...

    async def disconnect(self):
        """Clean up connection resources."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "category": self.category,
            "icon": self.icon,
            "description": self.description,
            "supported_extensions": self.supported_extensions,
            "requires_oauth": self.requires_oauth,
            "requires_api_key": self.requires_api_key,
        }


# ===========================================================================
# Cloud Storage Connectors
# ===========================================================================

class S3Connector(BaseConnector):
    kind = "S3"
    category = "cloud_storage"
    icon = "🪣"
    description = "Poll AWS S3 buckets for documents"
    supported_extensions = [".pdf", ".docx", ".xlsx", ".csv", ".json", ".txt", ".pptx"]
    requires_api_key = True

    async def connect(self) -> bool:
        import boto3
        self._client = boto3.client(
            "s3",
            aws_access_key_id=self.config.get("access_key"),
            aws_secret_access_key=self.config.get("secret_key"),
            region_name=self.config.get("region", "us-east-1"),
        )
        logger.info("S3 connected", bucket=self.config.get("bucket"))
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        bucket = self.config.get("bucket", "")
        prefix = self.config.get("prefix", "")
        response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return [
            {"id": obj["Key"], "name": obj["Key"], "size": obj["Size"],
             "modified": obj["LastModified"].isoformat()}
            for obj in response.get("Contents", [])
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        bucket = self.config.get("bucket", "")
        filename = Path(doc_id).name
        local_path = f"{dest_path}/{filename}"
        self._client.download_file(bucket, doc_id, local_path)
        return local_path


class AzureBlobConnector(BaseConnector):
    kind = "AzureBlob"
    category = "cloud_storage"
    icon = "☁️"
    description = "Sync from Azure Blob Storage containers"
    supported_extensions = [".pdf", ".docx", ".xlsx", ".csv", ".json", ".txt", ".pptx"]
    requires_api_key = True

    async def connect(self) -> bool:
        from azure.storage.blob import BlobServiceClient
        conn_str = self.config.get("connection_string", "")
        self._client = BlobServiceClient.from_connection_string(conn_str)
        logger.info("Azure Blob connected", container=self.config.get("container"))
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        container = self.config.get("container", "")
        container_client = self._client.get_container_client(container)
        blobs = container_client.list_blobs()
        return [
            {"id": blob.name, "name": blob.name, "size": blob.size,
             "modified": blob.last_modified.isoformat() if blob.last_modified else ""}
            for blob in blobs
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        container = self.config.get("container", "")
        blob_client = self._client.get_blob_client(container, doc_id)
        filename = Path(doc_id).name
        local_path = f"{dest_path}/{filename}"
        with open(local_path, "wb") as f:
            data = blob_client.download_blob()
            data.readinto(f)
        return local_path


class GCSConnector(BaseConnector):
    kind = "GCS"
    category = "cloud_storage"
    icon = "🌩️"
    description = "Sync from Google Cloud Storage buckets"
    supported_extensions = [".pdf", ".docx", ".xlsx", ".csv", ".json", ".txt", ".pptx"]
    requires_api_key = True

    async def connect(self) -> bool:
        from google.cloud import storage
        self._client = storage.Client()
        logger.info("GCS connected", bucket=self.config.get("bucket"))
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        bucket_name = self.config.get("bucket", "")
        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=self.config.get("prefix", ""))
        return [
            {"id": blob.name, "name": blob.name, "size": blob.size,
             "modified": blob.updated.isoformat() if blob.updated else ""}
            for blob in blobs
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        bucket = self._client.bucket(self.config.get("bucket", ""))
        blob = bucket.blob(doc_id)
        filename = Path(doc_id).name
        local_path = f"{dest_path}/{filename}"
        blob.download_to_filename(local_path)
        return local_path


# ===========================================================================
# Collaboration Connectors
# ===========================================================================

class SharePointConnector(BaseConnector):
    kind = "SharePoint"
    category = "collaboration"
    icon = "📂"
    description = "Sync from SharePoint document libraries"
    supported_extensions = [".docx", ".xlsx", ".pptx", ".pdf"]
    requires_oauth = True

    async def connect(self) -> bool:
        from office365.runtime.auth.client_credential import ClientCredential
        from office365.sharepoint.client_context import ClientContext
        site_url = self.config.get("site_url", "")
        client_id = self.config.get("client_id", "")
        client_secret = self.config.get("client_secret", "")
        credentials = ClientCredential(client_id, client_secret)
        self._ctx = ClientContext(site_url).with_credentials(credentials)
        logger.info("SharePoint connected", site=site_url)
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        library = self.config.get("library", "Shared Documents")
        lib = self._ctx.web.lists.get_by_title(library)
        items = lib.items.get().execute_query()
        return [
            {"id": str(item.properties.get("Id", "")),
             "name": item.properties.get("FileLeafRef", ""),
             "size": item.properties.get("File_x0020_Size", 0)}
            for item in items
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        library = self.config.get("library", "Shared Documents")
        file_url = f"/sites/{self.config.get('site_name', '')}/{library}/{doc_id}"
        local_path = f"{dest_path}/{Path(doc_id).name}"
        with open(local_path, "wb") as f:
            self._ctx.web.get_file_by_server_relative_url(file_url).download(f).execute_query()
        return local_path


class GoogleDriveConnector(BaseConnector):
    kind = "GoogleDrive"
    category = "collaboration"
    icon = "📁"
    description = "Watch and sync Google Drive folders"
    supported_extensions = [".docx", ".xlsx", ".pptx", ".pdf", ".txt"]
    requires_oauth = True

    async def connect(self) -> bool:
        logger.info("Google Drive connector initialized")
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        # Uses Google Drive API v3
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_authorized_user_info(self.config.get("credentials", {}))
        service = build("drive", "v3", credentials=creds)
        folder_id = self.config.get("folder_id", "root")
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType, size, modifiedTime)"
        ).execute()
        return [
            {"id": f["id"], "name": f["name"], "size": int(f.get("size", 0)),
             "modified": f.get("modifiedTime", "")}
            for f in results.get("files", [])
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        from google.oauth2.credentials import Credentials
        import io
        creds = Credentials.from_authorized_user_info(self.config.get("credentials", {}))
        service = build("drive", "v3", credentials=creds)
        request = service.files().get_media(fileId=doc_id)
        local_path = f"{dest_path}/{doc_id}"
        with open(local_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return local_path


class OneDriveConnector(BaseConnector):
    kind = "OneDrive"
    category = "collaboration"
    icon = "☁️"
    description = "Sync from OneDrive personal or business"
    supported_extensions = [".docx", ".xlsx", ".pptx", ".pdf", ".txt"]
    requires_oauth = True

    async def connect(self) -> bool:
        import msal
        app = msal.ConfidentialClientApplication(
            client_id=self.config.get("client_id", ""),
            client_credential=self.config.get("client_secret", ""),
            authority=f"https://login.microsoftonline.com/{self.config.get('tenant_id', 'common')}",
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        self._token = result.get("access_token", "")
        logger.info("OneDrive connected")
        return bool(self._token)

    async def list_documents(self) -> List[Dict[str, Any]]:
        import httpx
        folder = self.config.get("folder", "root")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://graph.microsoft.com/v1.0/me/drive/{folder}/children",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            data = resp.json()
        return [
            {"id": item["id"], "name": item["name"],
             "size": item.get("size", 0)}
            for item in data.get("value", [])
            if "file" in item
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://graph.microsoft.com/v1.0/me/drive/items/{doc_id}/content",
                headers={"Authorization": f"Bearer {self._token}"},
                follow_redirects=True,
            )
            local_path = f"{dest_path}/{doc_id}"
            with open(local_path, "wb") as f:
                f.write(resp.content)
        return local_path


class ConfluenceConnector(BaseConnector):
    kind = "Confluence"
    category = "collaboration"
    icon = "📄"
    description = "Crawl Confluence spaces and pages"
    supported_extensions = [".html"]
    requires_api_key = True

    async def connect(self) -> bool:
        from atlassian import Confluence
        self._client = Confluence(
            url=self.config.get("url", ""),
            username=self.config.get("username", ""),
            password=self.config.get("api_token", ""),
        )
        logger.info("Confluence connected", url=self.config.get("url"))
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        space = self.config.get("space_key", "")
        pages = self._client.get_all_pages_from_space(space, limit=100)
        return [
            {"id": p["id"], "name": p["title"], "size": 0}
            for p in pages
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        page = self._client.get_page_by_id(doc_id, expand="body.storage")
        html = page["body"]["storage"]["value"]
        local_path = f"{dest_path}/{doc_id}.html"
        with open(local_path, "w") as f:
            f.write(html)
        return local_path


# ===========================================================================
# Ticketing Connectors
# ===========================================================================

class ServiceNowConnector(BaseConnector):
    kind = "ServiceNow"
    category = "ticketing"
    icon = "🎫"
    description = "Sync ServiceNow incidents and knowledge base articles"
    supported_extensions = [".json"]
    requires_api_key = True

    async def connect(self) -> bool:
        self._base_url = self.config.get("instance_url", "")
        self._auth = (self.config.get("username", ""), self.config.get("password", ""))
        logger.info("ServiceNow connected", url=self._base_url)
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        import httpx
        table = self.config.get("table", "kb_knowledge")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/api/now/table/{table}",
                auth=self._auth,
                params={"sysparm_limit": 100},
            )
            data = resp.json()
        return [
            {"id": r["sys_id"], "name": r.get("short_description", r["sys_id"]), "size": 0}
            for r in data.get("result", [])
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        import httpx
        import json
        table = self.config.get("table", "kb_knowledge")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/api/now/table/{table}/{doc_id}",
                auth=self._auth,
            )
            data = resp.json()
        local_path = f"{dest_path}/{doc_id}.json"
        with open(local_path, "w") as f:
            json.dump(data.get("result", {}), f)
        return local_path


class JiraConnector(BaseConnector):
    kind = "Jira"
    category = "ticketing"
    icon = "🔷"
    description = "Sync Jira issues and epics"
    supported_extensions = [".json"]
    requires_api_key = True

    async def connect(self) -> bool:
        from atlassian import Jira
        self._client = Jira(
            url=self.config.get("url", ""),
            username=self.config.get("username", ""),
            password=self.config.get("api_token", ""),
        )
        logger.info("Jira connected", url=self.config.get("url"))
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        jql = self.config.get("jql", "project = PROJ ORDER BY created DESC")
        issues = self._client.jql(jql, limit=100)
        return [
            {"id": i["key"], "name": f"{i['key']}: {i['fields']['summary']}", "size": 0}
            for i in issues.get("issues", [])
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        import json
        issue = self._client.issue(doc_id)
        local_path = f"{dest_path}/{doc_id}.json"
        with open(local_path, "w") as f:
            json.dump(issue, f)
        return local_path


class GitHubConnector(BaseConnector):
    kind = "GitHub"
    category = "ticketing"
    icon = "🐙"
    description = "Sync GitHub issues, PRs, and repository files"
    supported_extensions = [".json", ".md"]
    requires_api_key = True

    async def connect(self) -> bool:
        from github import Github
        self._client = Github(self.config.get("token", ""))
        self._repo = self._client.get_repo(self.config.get("repo", ""))
        logger.info("GitHub connected", repo=self.config.get("repo"))
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        issues = self._repo.get_issues(state="all")
        return [
            {"id": str(i.number), "name": f"#{i.number}: {i.title}", "size": 0}
            for i in issues[:100]
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        import json
        issue = self._repo.get_issue(int(doc_id))
        data = {
            "number": issue.number, "title": issue.title,
            "body": issue.body, "state": issue.state,
            "labels": [l.name for l in issue.labels],
            "comments": [c.body for c in issue.get_comments()],
        }
        local_path = f"{dest_path}/{doc_id}.json"
        with open(local_path, "w") as f:
            json.dump(data, f)
        return local_path


# ===========================================================================
# Messaging Connectors
# ===========================================================================

class SlackConnector(BaseConnector):
    kind = "Slack"
    category = "messaging"
    icon = "💬"
    description = "Archive Slack channels"
    supported_extensions = [".json"]
    requires_oauth = True

    async def connect(self) -> bool:
        from slack_sdk import WebClient
        self._client = WebClient(token=self.config.get("token", ""))
        logger.info("Slack connected")
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        result = self._client.conversations_list(limit=100)
        return [
            {"id": ch["id"], "name": f"#{ch['name']}", "size": 0}
            for ch in result.get("channels", [])
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        import json
        result = self._client.conversations_history(channel=doc_id, limit=200)
        messages = result.get("messages", [])
        local_path = f"{dest_path}/{doc_id}.json"
        with open(local_path, "w") as f:
            json.dump(messages, f)
        return local_path


class TeamsConnector(BaseConnector):
    kind = "Teams"
    category = "messaging"
    icon = "🟦"
    description = "Archive Microsoft Teams chat history"
    supported_extensions = [".json"]
    requires_oauth = True

    async def connect(self) -> bool:
        import msal
        app = msal.ConfidentialClientApplication(
            client_id=self.config.get("client_id", ""),
            client_credential=self.config.get("client_secret", ""),
            authority=f"https://login.microsoftonline.com/{self.config.get('tenant_id', 'common')}",
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        self._token = result.get("access_token", "")
        logger.info("Teams connected")
        return bool(self._token)

    async def list_documents(self) -> List[Dict[str, Any]]:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/teams",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            data = resp.json()
        return [
            {"id": t["id"], "name": t.get("displayName", ""), "size": 0}
            for t in data.get("value", [])
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        import httpx
        import json
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://graph.microsoft.com/v1.0/teams/{doc_id}/channels",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            data = resp.json()
        local_path = f"{dest_path}/{doc_id}.json"
        with open(local_path, "w") as f:
            json.dump(data, f)
        return local_path


class EmailConnector(BaseConnector):
    kind = "Email"
    category = "messaging"
    icon = "📧"
    description = "Import EML/MSG/MBOX email archives"
    supported_extensions = [".eml", ".msg", ".mbox"]

    async def connect(self) -> bool:
        imap_host = self.config.get("imap_host", "")
        if imap_host:
            from imapclient import IMAPClient
            self._client = IMAPClient(imap_host, ssl=True)
            self._client.login(
                self.config.get("username", ""),
                self.config.get("password", ""),
            )
            logger.info("Email IMAP connected", host=imap_host)
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        folder = self.config.get("folder", "INBOX")
        self._client.select_folder(folder)
        messages = self._client.search(["NOT", "DELETED"])
        return [
            {"id": str(uid), "name": f"Email #{uid}", "size": 0}
            for uid in messages[:100]
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        raw = self._client.fetch([int(doc_id)], ["RFC822"])
        local_path = f"{dest_path}/{doc_id}.eml"
        with open(local_path, "wb") as f:
            f.write(raw[int(doc_id)][b"RFC822"])
        return local_path


# ===========================================================================
# Data & Integration Connectors
# ===========================================================================

class DatabaseConnector(BaseConnector):
    kind = "Database"
    category = "database"
    icon = "🗄️"
    description = "Execute SQL or NoSQL queries"
    supported_extensions = [".json", ".csv"]
    requires_api_key = True

    async def connect(self) -> bool:
        self._dsn = self.config.get("dsn", "")
        logger.info("Database connector configured")
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        import sqlalchemy
        engine = sqlalchemy.create_engine(self._dsn)
        inspector = sqlalchemy.inspect(engine)
        tables = inspector.get_table_names()
        return [
            {"id": t, "name": f"Table: {t}", "size": 0}
            for t in tables
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        import pandas as pd
        import sqlalchemy
        engine = sqlalchemy.create_engine(self._dsn)
        query = self.config.get("query", f"SELECT * FROM {doc_id} LIMIT 10000")
        df = pd.read_sql(query, engine)
        local_path = f"{dest_path}/{doc_id}.csv"
        df.to_csv(local_path, index=False)
        return local_path


class WebhookConnector(BaseConnector):
    kind = "Webhook"
    category = "database"
    icon = "🔗"
    description = "Receive real-time data pushes via webhook"
    supported_extensions = [".json"]
    requires_api_key = True

    async def connect(self) -> bool:
        logger.info("Webhook connector ready")
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        return []  # Webhooks are push-based

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        return ""  # Handled via API endpoint


# ===========================================================================
# Local Connector
# ===========================================================================

class LocalConnector(BaseConnector):
    kind = "Local"
    category = "local"
    icon = "📤"
    description = "Direct file upload from local machine"
    supported_extensions = [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".json",
                           ".html", ".md", ".eml", ".msg", ".parquet", ".log", ".jsonl"]

    async def connect(self) -> bool:
        return True

    async def list_documents(self) -> List[Dict[str, Any]]:
        upload_dir = self.config.get("upload_dir", "/app/uploads")
        p = Path(upload_dir)
        if not p.exists():
            return []
        return [
            {"id": f.name, "name": f.name, "size": f.stat().st_size}
            for f in p.iterdir() if f.is_file()
        ]

    async def fetch_document(self, doc_id: str, dest_path: str) -> str:
        return f"{self.config.get('upload_dir', '/app/uploads')}/{doc_id}"


# ===========================================================================
# Registry
# ===========================================================================
CONNECTOR_REGISTRY: Dict[str, type] = {
    "S3": S3Connector,
    "AzureBlob": AzureBlobConnector,
    "GCS": GCSConnector,
    "SharePoint": SharePointConnector,
    "GoogleDrive": GoogleDriveConnector,
    "OneDrive": OneDriveConnector,
    "Confluence": ConfluenceConnector,
    "ServiceNow": ServiceNowConnector,
    "Jira": JiraConnector,
    "GitHub": GitHubConnector,
    "Slack": SlackConnector,
    "Teams": TeamsConnector,
    "Email": EmailConnector,
    "Database": DatabaseConnector,
    "Webhook": WebhookConnector,
    "Local": LocalConnector,
}


def get_connector(kind: str, config: Dict[str, Any] = None) -> BaseConnector:
    """Get a connector instance by kind."""
    cls = CONNECTOR_REGISTRY.get(kind)
    if cls is None:
        raise ValueError(f"Unknown connector kind: {kind}")
    return cls(config=config)
