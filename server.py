from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import subprocess
import shutil
import json
import os
from typing import Optional, List

mcp = FastMCP("restful-wp-cli")


def wp_cli_available() -> bool:
    """Check if wp-cli is available on the system."""
    return shutil.which("wp") is not None


def run_wp_cli(args: List[str], path: Optional[str] = None, ssh: Optional[str] = None, http_target: Optional[str] = None) -> dict:
    """Run a WP-CLI command and return the result."""
    if not wp_cli_available():
        return {"error": "WP-CLI (wp) is not installed or not in PATH. Please install WP-CLI first: https://wp-cli.org/"}

    cmd = ["wp"]

    if path:
        cmd += [f"--path={path}"]
    if ssh:
        cmd += [f"--ssh={ssh}"]
    if http_target:
        cmd += [f"--http={http_target}"]

    cmd += args
    cmd += ["--format=json"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            return {"error": stderr or "WP-CLI command failed", "returncode": result.returncode, "stdout": stdout}

        try:
            return {"success": True, "data": json.loads(stdout)}
        except json.JSONDecodeError:
            return {"success": True, "data": stdout}
    except subprocess.TimeoutExpired:
        return {"error": "WP-CLI command timed out after 60 seconds"}
    except Exception as e:
        return {"error": str(e)}


def run_wp_cli_raw(args: List[str], path: Optional[str] = None, ssh: Optional[str] = None, http_target: Optional[str] = None) -> dict:
    """Run a WP-CLI command without forcing JSON format."""
    if not wp_cli_available():
        return {"error": "WP-CLI (wp) is not installed or not in PATH."}

    cmd = ["wp"]

    if path:
        cmd += [f"--path={path}"]
    if ssh:
        cmd += [f"--ssh={ssh}"]
    if http_target:
        cmd += [f"--http={http_target}"]

    cmd += args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "WP-CLI command timed out after 60 seconds"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def rest_discover(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None
) -> dict:
    """
    Auto-discover WP REST API endpoints from a WordPress site.
    Use --path for local installs, --ssh for remote hosts, or --http for HTTP discovery.
    Returns all available REST resource types (e.g., post, page, user, category).
    """
    return run_wp_cli_raw(["rest"], path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_list(
    resource: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    per_page: Optional[int] = None,
    page: Optional[int] = None,
    search: Optional[str] = None,
    fields: Optional[str] = None
) -> dict:
    """
    List items of a WP REST API resource type (e.g., post, page, user, category, tag, comment, attachment).
    Examples: resource='post', resource='page', resource='user', resource='category'.
    Optionally filter by per_page, page, search query, or specific fields (comma-separated).
    """
    args = ["rest", resource, "list"]
    if per_page:
        args += [f"--per_page={per_page}"]
    if page:
        args += [f"--page={page}"]
    if search:
        args += [f"--search={search}"]
    if fields:
        args += [f"--fields={fields}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_get(
    resource: str,
    resource_id: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    fields: Optional[str] = None
) -> dict:
    """
    Get a single WP REST API resource by its ID.
    Example: resource='post', resource_id='1' to get post with ID 1.
    Optionally specify fields (comma-separated) to return only specific fields.
    """
    args = ["rest", resource, "get", resource_id]
    if fields:
        args += [f"--fields={fields}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_create(
    resource: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    status: Optional[str] = None,
    slug: Optional[str] = None,
    excerpt: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    extra_params: Optional[str] = None
) -> dict:
    """
    Create a new WP REST API resource (post, page, user, category, tag, etc.).
    Provide title/content/status for posts and pages.
    Provide name/description for taxonomies.
    Provide username/email for users.
    extra_params: additional CLI params as a space-separated string like '--param=value --param2=value2'.
    """
    args = ["rest", resource, "create"]
    if title:
        args += [f"--title={title}"]
    if content:
        args += [f"--content={content}"]
    if status:
        args += [f"--status={status}"]
    if slug:
        args += [f"--slug={slug}"]
    if excerpt:
        args += [f"--excerpt={excerpt}"]
    if name:
        args += [f"--name={name}"]
    if description:
        args += [f"--description={description}"]
    if email:
        args += [f"--email={email}"]
    if username:
        args += [f"--username={username}"]
    if extra_params:
        for param in extra_params.split():
            args.append(param)
    return run_wp_cli_raw(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_update(
    resource: str,
    resource_id: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    status: Optional[str] = None,
    slug: Optional[str] = None,
    excerpt: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    extra_params: Optional[str] = None
) -> dict:
    """
    Update an existing WP REST API resource by its ID.
    Example: resource='post', resource_id='42', title='New Title'.
    extra_params: additional CLI params as a space-separated string like '--param=value'.
    """
    args = ["rest", resource, "update", resource_id]
    if title:
        args += [f"--title={title}"]
    if content:
        args += [f"--content={content}"]
    if status:
        args += [f"--status={status}"]
    if slug:
        args += [f"--slug={slug}"]
    if excerpt:
        args += [f"--excerpt={excerpt}"]
    if name:
        args += [f"--name={name}"]
    if description:
        args += [f"--description={description}"]
    if extra_params:
        for param in extra_params.split():
            args.append(param)
    return run_wp_cli_raw(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_delete(
    resource: str,
    resource_id: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    force: bool = False
) -> dict:
    """
    Delete a WP REST API resource by its ID.
    Set force=True to bypass trash and permanently delete (for posts/pages).
    Example: resource='post', resource_id='42'.
    """
    args = ["rest", resource, "delete", resource_id]
    if force:
        args.append("--force")
    return run_wp_cli_raw(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_post_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    per_page: Optional[int] = 10,
    page: Optional[int] = 1,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> dict:
    """
    List WordPress posts via the REST API.
    Filter by status (publish, draft, private, etc.), search term, pagination.
    """
    args = ["rest", "post", "list"]
    if per_page:
        args += [f"--per_page={per_page}"]
    if page:
        args += [f"--page={page}"]
    if status:
        args += [f"--status={status}"]
    if search:
        args += [f"--search={search}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_page_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    per_page: Optional[int] = 10,
    page: Optional[int] = 1,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> dict:
    """
    List WordPress pages via the REST API.
    Filter by status (publish, draft, private, etc.), search term, pagination.
    """
    args = ["rest", "page", "list"]
    if per_page:
        args += [f"--per_page={per_page}"]
    if page:
        args += [f"--page={page}"]
    if status:
        args += [f"--status={status}"]
    if search:
        args += [f"--search={search}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_user_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    per_page: Optional[int] = 10,
    page: Optional[int] = 1,
    search: Optional[str] = None,
    roles: Optional[str] = None
) -> dict:
    """
    List WordPress users via the REST API.
    Filter by search term, roles (comma-separated), pagination.
    """
    args = ["rest", "user", "list"]
    if per_page:
        args += [f"--per_page={per_page}"]
    if page:
        args += [f"--page={page}"]
    if search:
        args += [f"--search={search}"]
    if roles:
        args += [f"--roles={roles}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_comment_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    per_page: Optional[int] = 10,
    page: Optional[int] = 1,
    post_id: Optional[str] = None,
    status: Optional[str] = None
) -> dict:
    """
    List WordPress comments via the REST API.
    Filter by post_id, status (approved, hold, spam, trash), pagination.
    """
    args = ["rest", "comment", "list"]
    if per_page:
        args += [f"--per_page={per_page}"]
    if page:
        args += [f"--page={page}"]
    if post_id:
        args += [f"--post={post_id}"]
    if status:
        args += [f"--status={status}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_category_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    per_page: Optional[int] = 10,
    page: Optional[int] = 1,
    search: Optional[str] = None
) -> dict:
    """
    List WordPress categories via the REST API.
    Filter by search term, pagination.
    """
    args = ["rest", "category", "list"]
    if per_page:
        args += [f"--per_page={per_page}"]
    if page:
        args += [f"--page={page}"]
    if search:
        args += [f"--search={search}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_tag_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    per_page: Optional[int] = 10,
    page: Optional[int] = 1,
    search: Optional[str] = None
) -> dict:
    """
    List WordPress tags via the REST API.
    Filter by search term, pagination.
    """
    args = ["rest", "tag", "list"]
    if per_page:
        args += [f"--per_page={per_page}"]
    if page:
        args += [f"--page={page}"]
    if search:
        args += [f"--search={search}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def rest_media_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None,
    per_page: Optional[int] = 10,
    page: Optional[int] = 1,
    search: Optional[str] = None,
    media_type: Optional[str] = None
) -> dict:
    """
    List WordPress media attachments via the REST API.
    Filter by search term, media_type (image, video, audio, application, text), pagination.
    """
    args = ["rest", "attachment", "list"]
    if per_page:
        args += [f"--per_page={per_page}"]
    if page:
        args += [f"--page={page}"]
    if search:
        args += [f"--search={search}"]
    if media_type:
        args += [f"--media_type={media_type}"]
    return run_wp_cli(args, path=path, ssh=ssh, http_target=http_target)


@mcp.tool()
async def wp_cli_info(
    path: Optional[str] = None
) -> dict:
    """
    Get WP-CLI version and environment information.
    Optionally specify a WordPress installation path.
    """
    return run_wp_cli_raw(["cli", "info"], path=path)


@mcp.tool()
async def wp_site_info(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    http_target: Optional[str] = None
) -> dict:
    """
    Get WordPress site information including URL, name, description, and WordPress version.
    """
    result = {}

    option_result = run_wp_cli_raw(
        ["option", "get", "siteurl"],
        path=path, ssh=ssh, http_target=http_target
    )
    result["siteurl"] = option_result.get("stdout", "")

    name_result = run_wp_cli_raw(
        ["option", "get", "blogname"],
        path=path, ssh=ssh, http_target=http_target
    )
    result["blogname"] = name_result.get("stdout", "")

    desc_result = run_wp_cli_raw(
        ["option", "get", "blogdescription"],
        path=path, ssh=ssh, http_target=http_target
    )
    result["blogdescription"] = desc_result.get("stdout", "")

    ver_result = run_wp_cli_raw(
        ["core", "version"],
        path=path, ssh=ssh, http_target=http_target
    )
    result["wordpress_version"] = ver_result.get("stdout", "")

    return result


@mcp.tool()
async def wp_plugin_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    status: Optional[str] = None
) -> dict:
    """
    List installed WordPress plugins.
    Optionally filter by status: active, inactive, must-use, drop-in.
    """
    args = ["plugin", "list"]
    if status:
        args += [f"--status={status}"]
    return run_wp_cli(args, path=path, ssh=ssh)


@mcp.tool()
async def wp_theme_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    status: Optional[str] = None
) -> dict:
    """
    List installed WordPress themes.
    Optionally filter by status: active, inactive, parent.
    """
    args = ["theme", "list"]
    if status:
        args += [f"--status={status}"]
    return run_wp_cli(args, path=path, ssh=ssh)


@mcp.tool()
async def wp_db_query(
    sql: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None
) -> dict:
    """
    Run a raw SQL query against a WordPress database using WP-CLI.
    WARNING: Use with extreme caution. Only SELECT queries are recommended.
    Example: sql='SELECT ID, post_title FROM wp_posts WHERE post_status="publish" LIMIT 5'
    """
    if not wp_cli_available():
        return {"error": "WP-CLI is not available."}

    cmd = ["wp"]
    if path:
        cmd += [f"--path={path}"]
    if ssh:
        cmd += [f"--ssh={ssh}"]
    cmd += ["db", "query", sql, "--skip-column-names"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "Query timed out after 30 seconds"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def wp_search_replace(
    search: str,
    replace: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    dry_run: bool = True,
    tables: Optional[str] = None
) -> dict:
    """
    Search and replace strings in the WordPress database.
    By default runs as a dry-run (no changes made). Set dry_run=False to apply changes.
    Optionally specify comma-separated table names to limit scope.
    Example: search='http://old-domain.com', replace='https://new-domain.com'.
    """
    args = ["search-replace", search, replace]
    if dry_run:
        args.append("--dry-run")
    if tables:
        for table in tables.split(","):
            args.append(table.strip())
    return run_wp_cli_raw(args, path=path, ssh=ssh)


@mcp.tool()
async def wp_cache_flush(
    path: Optional[str] = None,
    ssh: Optional[str] = None
) -> dict:
    """
    Flush the WordPress object cache.
    """
    return run_wp_cli_raw(["cache", "flush"], path=path, ssh=ssh)


@mcp.tool()
async def wp_cron_event_list(
    path: Optional[str] = None,
    ssh: Optional[str] = None
) -> dict:
    """
    List scheduled WordPress cron events.
    """
    return run_wp_cli(["cron", "event", "list"], path=path, ssh=ssh)


@mcp.tool()
async def wp_cron_run(
    hook: Optional[str] = None,
    path: Optional[str] = None,
    ssh: Optional[str] = None
) -> dict:
    """
    Run WordPress cron events. Optionally specify a specific hook name to run only that event.
    """
    args = ["cron", "event", "run"]
    if hook:
        args.append(hook)
    else:
        args.append("--due-now")
    return run_wp_cli_raw(args, path=path, ssh=ssh)


@mcp.tool()
async def wp_rewrite_flush(
    path: Optional[str] = None,
    ssh: Optional[str] = None,
    hard: bool = False
) -> dict:
    """
    Flush WordPress rewrite rules. Set hard=True to do a hard flush (regenerates .htaccess).
    """
    args = ["rewrite", "flush"]
    if hard:
        args.append("--hard")
    return run_wp_cli_raw(args, path=path, ssh=ssh)


@mcp.tool()
async def wp_option_get(
    option_name: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None
) -> dict:
    """
    Get a WordPress option value by name.
    Example: option_name='siteurl', option_name='blogname', option_name='active_plugins'.
    """
    return run_wp_cli_raw(["option", "get", option_name], path=path, ssh=ssh)


@mcp.tool()
async def wp_option_update(
    option_name: str,
    option_value: str,
    path: Optional[str] = None,
    ssh: Optional[str] = None
) -> dict:
    """
    Update a WordPress option value.
    Example: option_name='blogname', option_value='My New Blog Name'.
    WARNING: Use with caution as incorrect values can break your site.
    """
    return run_wp_cli_raw(["option", "update", option_name, option_value], path=path, ssh=ssh)


@mcp.tool()
async def wp_core_check_update(
    path: Optional[str] = None,
    ssh: Optional[str] = None
) -> dict:
    """
    Check if a WordPress core update is available.
    """
    return run_wp_cli(["core", "check-update"], path=path, ssh=ssh)


@mcp.tool()
async def wp_plugin_check_update(
    path: Optional[str] = None,
    ssh: Optional[str] = None
) -> dict:
    """
    Check if any WordPress plugin updates are available.
    """
    return run_wp_cli(["plugin", "list", "--update=available"], path=path, ssh=ssh)


@mcp.tool()
async def wp_cli_check_available() -> dict:
    """
    Check if WP-CLI is installed and available on this server.
    Returns version information if available.
    """
    available = wp_cli_available()
    if not available:
        return {
            "available": False,
            "message": "WP-CLI is not installed or not in PATH. Install from https://wp-cli.org/"
        }

    result = run_wp_cli_raw(["cli", "version"])
    return {
        "available": True,
        "version_info": result.get("stdout", ""),
        "message": "WP-CLI is available and ready to use."
    }




_SERVER_SLUG = "wp-cli-restful"

def _track(tool_name: str, ua: str = ""):
    try:
        import urllib.request, json as _json
        data = _json.dumps({"slug": _SERVER_SLUG, "event": "tool_call", "tool": tool_name, "user_agent": ua}).encode()
        req = urllib.request.Request("https://www.volspan.dev/api/analytics/event", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass

async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

mcp_app = mcp.http_app(transport="streamable-http", stateless_http=True)

class _FixAcceptHeader:
    """Ensure Accept header includes both types FastMCP requires."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            accept = headers.get(b"accept", b"").decode()
            if "text/event-stream" not in accept:
                new_headers = [(k, v) for k, v in scope["headers"] if k != b"accept"]
                new_headers.append((b"accept", b"application/json, text/event-stream"))
                scope = dict(scope, headers=new_headers)
        await self.app(scope, receive, send)

app = _FixAcceptHeader(Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", mcp_app),
    ],
    lifespan=mcp_app.lifespan,
))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
