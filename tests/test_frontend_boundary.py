"""Exercise the production SPA route without starting optional ML/Oracle services."""

import ast
import os
from pathlib import Path
import tempfile
import unittest

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from httpx import ASGITransport, AsyncClient


class FrontendBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.dist = self.root / "frontend" / "dist"
        self.dist.mkdir(parents=True)
        (self.dist / "index.html").write_text("synthetic SPA", encoding="utf8")
        (self.dist / "logo.txt").write_text("public asset", encoding="utf8")
        (self.root / "private.txt").write_text("synthetic private data", encoding="utf8")
        # Compile the actual registered route, retaining its decorator. Importing
        # server itself would initialize unrelated optional NLP/Oracle services.
        source = Path(__file__).resolve().parents[1] / "server.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        route = next(node for node in ast.walk(tree)
                     if isinstance(node, ast.AsyncFunctionDef) and node.name == "serve_frontend")
        app = FastAPI()
        namespace = {"app": app, "os": os, "Path": Path,
                     "frontend_dist": str(self.dist), "FileResponse": FileResponse,
                     "HTTPException": HTTPException}
        exec(compile(ast.Module(body=[route], type_ignores=[]), str(source), "exec"), namespace)
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def test_encoded_parent_path_cannot_serve_private_files(self):
        response = await self.client.get("/%2e%2e/%2e%2e/private.txt")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("synthetic private data", response.text)

    async def test_windows_separator_parent_path_cannot_serve_private_files(self):
        response = await self.client.get("/..%5c..%5cprivate.txt")
        self.assertEqual(response.status_code, 404)

    async def test_public_asset_and_client_side_route_still_work(self):
        asset = await self.client.get("/logo.txt")
        route = await self.client.get("/jobs/synthetic")
        self.assertEqual((asset.status_code, asset.text), (200, "public asset"))
        self.assertEqual((route.status_code, route.text), (200, "synthetic SPA"))


if __name__ == "__main__":
    unittest.main()
