import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import aiofiles

from app.tools import BaseTool


class FileCreationTool(BaseTool):
    """
    Creates files of different types (txt, md, pdf) based on user requirements.
    Currently supports: txt, md
    Future support: pdf, docx, html
    """

    def __init__(self, base_directory: Optional[str] = None):
        """
        Initialize FileCreationTool.

        Args:
            base_directory: Base directory where files will be created.
                          If None, uses uploads/generated/{session_id}/ when session_id is provided,
                          otherwise uses current working directory.
        """
        # Default base directory will be set based on session_id in execute method
        self.default_base_directory = base_directory or os.getcwd()

    @property
    def name(self) -> str:
        return "create_file"

    @property
    def description(self) -> str:
        return "Creates a file with specified content and type. Supports .txt and .md formats. Can optionally append timestamp to filename and create files in subdirectories. If content is not provided or empty, it will be automatically generated based on the user's request."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to create (without extension)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "file_type": {
                    "type": "string",
                    "enum": ["txt", "md"],
                    "description": "Type of file to create: 'txt' for plain text or 'md' for Markdown",
                    "default": "txt"
                },
                "subdirectory": {
                    "type": "string",
                    "description": "Optional subdirectory path within base directory (e.g., 'notes/work')",
                    "default": ""
                },
                "append_timestamp": {
                    "type": "boolean",
                    "description": "Whether to append timestamp to filename (default: false)",
                    "default": False
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Whether to overwrite if file exists (default: false)",
                    "default": False
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID (UUID) for organizing generated files (automatically provided)",
                    "default": None
                }
            },
            "required": ["filename", "content"]
        }

    async def execute(
            self,
            filename: str,
            content: str,
            file_type: str = "txt",
            subdirectory: str = "",
            append_timestamp: bool = False,
            overwrite: bool = False,
            session_id: Optional[str] = None
    ) -> str:
        """
        Create a file with the specified content and type.

        Args:
            filename: Name of the file (without extension)
            content: Content to write to the file
            file_type: Type of file ('txt' or 'md')
            subdirectory: Optional subdirectory path
            append_timestamp: Whether to append timestamp to filename
            overwrite: Whether to overwrite existing file
            session_id: Session ID for organizing files (automatically provided via request_context)

        Returns:
            Success message with file path or error message
        """
        try:
            # Validate file type
            if file_type not in ["txt", "md"]:
                return f"Error: Unsupported file type '{file_type}'. Currently supported: txt, md"

            # Determine base directory based on session_id
            if session_id is not None:
                # Use uploads/generated/{session_id}/ as base directory
                # session_id can be UUID or string, convert to string
                session_id_str = str(session_id) if session_id else None
                if session_id_str:
                    base_dir = Path("uploads") / "generated" / session_id_str
                    base_directory = str(base_dir.resolve())
                else:
                    base_directory = self.default_base_directory
            else:
                # Fallback to default base directory
                base_directory = self.default_base_directory

            # Sanitize filename
            filename = self._sanitize_filename(filename)

            # Add timestamp if requested
            if append_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{filename}_{timestamp}"

            # Add file extension
            filename_with_ext = f"{filename}.{file_type}"
            # Build full path
            if subdirectory:
                target_dir = os.path.join(base_directory, subdirectory)
                self._ensure_directory_exists(target_dir)
            else:
                target_dir = base_directory
                self._ensure_directory_exists(target_dir)

            file_path = os.path.join(target_dir, filename_with_ext)

            # Check if file exists
            if os.path.exists(file_path) and not overwrite:
                # Use relative path in error message for privacy
                session_id_str = str(session_id) if session_id else None
                error_path = filename_with_ext if session_id_str is None else f"uploads/generated/{session_id_str}/{filename_with_ext}"
                return f"Error: File already exists: '{error_path}'. Set overwrite=True to replace it."

            # Prepare content based on file type
            formatted_content = self._format_content(
                content, file_type, filename)

            # Write file asynchronously
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(formatted_content)

            # Get file info
            file_size = os.path.getsize(file_path)
            file_size_kb = file_size / 1024

            # Create relative path for display (privacy-friendly)
            session_id_str = str(session_id) if session_id else None
            if session_id_str is not None:
                # Show relative path from uploads/generated/{session_id}/
                display_path = f"uploads/generated/{session_id_str}/{filename_with_ext}"
                if subdirectory:
                    display_path = f"uploads/generated/{session_id_str}/{subdirectory}/{filename_with_ext}"
            else:
                # Fallback to just filename
                display_path = filename_with_ext

            # Create structured response with file metadata
            # Format: human-readable message + JSON metadata at the end
            file_metadata = {
                "file_created": True,
                "file_path": file_path,  # Full path for internal use
                "filename": filename_with_ext,
                "file_type": file_type,
                "file_size": file_size,
                "relative_path": str(Path(file_path).relative_to(Path.cwd())) if Path(file_path).is_relative_to(
                    Path.cwd()) else file_path
            }

            # Embed metadata as JSON comment at the end (for parsing)
            metadata_json = json.dumps(file_metadata)

            return f"""File created successfully!

File: {filename_with_ext}
Location: {display_path}
Type: {file_type.upper()}
Size: {file_size_kb:.2f} KB
Lines: {len(formatted_content.splitlines())}

<!--FILE_METADATA:{metadata_json}-->"""

        except PermissionError:
            # Don't expose full directory path in error
            session_id_str = str(session_id) if session_id else None
            error_dir = "the target directory" if session_id_str is None else f"uploads/generated/{session_id_str}/"
            return f"Error: Permission denied. Cannot write to {error_dir}"
        except OSError as e:
            # Don't expose system paths in error messages
            error_msg = str(e)
            # Remove absolute paths from error message if present
            if os.path.sep in error_msg and len(error_msg) > 100:
                error_msg = "Failed to create file due to system error"
            return f"Error: Failed to create file - {error_msg}"
        except Exception as e:
            return f"Error creating file: {str(e)}"

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove invalid characters for filenames
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')

        # Ensure filename is not empty
        if not filename:
            filename = "untitled"

        return filename

    def _format_content(self, content: str, file_type: str, filename: str) -> str:
        """
        Format content based on file type.

        Args:
            content: Original content
            file_type: Type of file
            filename: Name of the file

        Returns:
            Formatted content
        """
        if file_type == "md":
            # Add markdown header if not present
            if not content.strip().startswith('#'):
                formatted = f"# {filename}\n\n{content}"
            else:
                formatted = content
        else:
            # Plain text - use as is
            formatted = content

        # Ensure content ends with newline
        if not formatted.endswith('\n'):
            formatted += '\n'

        return formatted

    def _ensure_directory_exists(self, directory: str) -> None:
        """
        Ensure directory exists, create if it doesn't.

        Args:
            directory: Directory path to check/create
        """
        Path(directory).mkdir(parents=True, exist_ok=True)
