from tree_sitter_languages import get_parser

def chunk_tree(code_string: str, language: str, file_name: str = "unknown", max_lines: int = 50):
    parser = get_parser(language)
    tree = parser.parse(bytes(code_string, "utf8"))
    root = tree.root_node
    chunks = []

    SKIP_TYPES = {"comment", "newline", "", "module", 
              "import_statement", "import_from_statement"}

    # node types that should be expanded into their children
    EXPAND_TYPES = {"class_definition", "decorated_definition"}

    def extract_chunks(node, parent_name: str = None):
        if node.type in SKIP_TYPES:
            return

        chunk_text = code_string[node.start_byte:node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        line_count = end_line - start_line

        # for classes — add the class chunk itself, then recurse into methods
        if node.type in EXPAND_TYPES:
            name_node = node.child_by_field_name("name")
            class_name = code_string[name_node.start_byte:name_node.end_byte] if name_node else "unknown"

            # add the class signature as its own small chunk
            chunks.append({
                "file": file_name,
                "node_type": node.type,
                "name": class_name,
                "text": chunk_text[:200],   # just the class header
                "start_line": start_line,
                "end_line": end_line,
            })

            # recurse into class body to get individual methods
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    extract_chunks(child, parent_name=class_name)

        # for large functions — split into sub-chunks if too long
        elif node.type == "function_definition" and line_count > max_lines:
            name_node = node.child_by_field_name("name")
            fn_name = code_string[name_node.start_byte:name_node.end_byte] if name_node else "unknown"

            # split text into smaller pieces
            lines = chunk_text.split("\n")
            for i in range(0, len(lines), max_lines):
                sub_chunk = "\n".join(lines[i:i + max_lines])
                chunks.append({
                    "file": file_name,
                    "node_type": "function_definition",
                    "name": fn_name,
                    "parent": parent_name,
                    "text": sub_chunk,
                    "start_line": start_line + i,
                    "end_line": min(start_line + i + max_lines, end_line),
                })

        # everything else — imports, assignments, normal functions
        else:
            name_node = node.child_by_field_name("name")
            name = code_string[name_node.start_byte:name_node.end_byte] if name_node else node.type

            chunks.append({
                "file": file_name,
                "node_type": node.type,
                "name": name,
                "parent": parent_name,
                "text": chunk_text,
                "start_line": start_line,
                "end_line": end_line,
            })

    for node in root.children:
        extract_chunks(node)

    return chunks


# test it
