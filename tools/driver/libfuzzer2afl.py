#!/usr/bin/env python3
"""
Convert a LibFuzzer compatible program to AFL++ compatible program.
This script takes a directory of C/C++ source files written for LibFuzzer and converts them to be compatible with AFL++.
"""

import re
import argparse
import os
import sys
import glob
from log import log_info, log_error, log_warning

def convert_libfuzzer_to_afl(input_content):
    """
    Convert LibFuzzer fuzzing target to AFL++ compatible code.
    
    Main approach:
    1. Keep all original code
    2. Add AFL++ main function that will call the original LLVMFuzzerTestOneInput
    3. Add required headers if missing
    """
    
    # Find the LLVMFuzzerTestOneInput function signature
    fuzzer_func_pattern = r'(extern\s+)?(int|size_t)?\s+LLVMFuzzerTestOneInput\s*\(\s*(const\s+)?(unsigned\s+)?(char|uint8_t)\s*\*\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*(size_t|unsigned(\s+int)?|long(\s+int)?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\)'
    match = re.search(fuzzer_func_pattern, input_content)
    
    if not match:
        return input_content, False
    
    # Extract parameter names
    data_param = match.group(6)  # The buffer parameter name
    size_param = match.group(10)  # The size parameter name
    
    # Find existing includes
    includes_pattern = r'((?:#include\s+[<"][^>"\n]+[>"]\s*\n)+)'
    includes_match = re.search(includes_pattern, input_content)
    
    # Prepare required headers
    required_headers = ["<stdio.h>", "<stdlib.h>", "<stdint.h>", "<string.h>", "<unistd.h>", "<sys/stat.h>"]
    
    # If we found existing includes, add our required headers there if needed
    if includes_match:
        includes_section = includes_match.group(1)
        
        # Add any missing required headers
        for header in required_headers:
            if header not in includes_section:
                includes_section += f"#include {header}\n"
        
        # Add some blank lines after includes for better formatting
        includes_section += "\n\n"
        
        # Replace original includes with our expanded version
        input_content = input_content.replace(includes_match.group(1), includes_section)
    else:
        # If no includes found, add all required headers at the beginning
        header_block = ""
        for header in required_headers:
            header_block += f"#include {header}\n"
        # Add some blank lines after includes for better formatting
        header_block += "\n\n"
        input_content = header_block + input_content
    
    # Create the AFL-compatible main function
    afl_main = f"""
int main(int argc, char **argv) {{
    FILE *f;
    uint8_t *buf = NULL;
    size_t len = 0;
    struct stat st;
    
    if (argc != 2) {{
        fprintf(stderr, "Usage: %s <input_file>\\n", argv[0]);
        return 1;
    }}
    
    // Open the input file
    f = fopen(argv[1], "rb");
    if (!f) {{
        fprintf(stderr, "Error opening file: %s\\n", argv[1]);
        return 2;
    }}
    
    // Get file size
    if (fstat(fileno(f), &st) != 0) {{
        fprintf(stderr, "Error getting file size\\n");
        fclose(f);
        return 3;
    }}
    
    // Allocate memory for the file content
    len = st.st_size;
    buf = (uint8_t *)malloc(len);
    if (!buf) {{
        fprintf(stderr, "Memory allocation failed\\n");
        fclose(f);
        return 4;
    }}
    
    // Read the file content
    if (fread(buf, 1, len, f) != len) {{
        fprintf(stderr, "Error reading file\\n");
        free(buf);
        fclose(f);
        return 5;
    }}
    
    fclose(f);
    
    // Call the fuzzing function
    int ret = LLVMFuzzerTestOneInput(buf, len);
    
    // Clean up
    free(buf);
    return ret;
}}

"""
    
    # Insert the AFL main function at the end of the file
    # This preserves all original code
    afl_content = input_content + "\n" + afl_main
    
    return afl_content, True

def convert_harness_file(input_file, output_file):
    """Convert a single LibFuzzer harness file to AFL++ format"""
    try:
        with open(input_file, 'r') as f:
            input_content = f.read()
    except Exception as e:
        log_error(f"Error reading input file {input_file}: {e}")
        return False
    
    # Convert the content
    afl_content, success = convert_libfuzzer_to_afl(input_content)
    
    if not success:
        log_error(f"Could not find LLVMFuzzerTestOneInput function in {input_file}")
        return False
    
    # Write output file
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(afl_content)
        log_info(f"Successfully converted {input_file} to {output_file}")
        return True
    except Exception as e:
        log_error(f"Error writing output file {output_file}: {e}")
        return False

def process_file(input_file, output_dir):
    """Process a single file and convert it to AFL++ compatible format"""
    try:
        with open(input_file, 'r') as f:
            input_content = f.read()
    except Exception as e:
        print(f"Error reading input file {input_file}: {e}", file=sys.stderr)
        return False
    
    # Convert the content
    afl_content, success = convert_libfuzzer_to_afl(input_content)
    
    if not success:
        print(f"Could not find LLVMFuzzerTestOneInput function in {input_file}.", file=sys.stderr)
        return False
    
    # Determine output file path
    base_name = os.path.basename(input_file)
    base, ext = os.path.splitext(base_name)
    output_file = os.path.join(output_dir, f"{base}_afl{ext}")
    
    # Write output file
    try:
        with open(output_file, 'w') as f:
            f.write(afl_content)
        print(f"Successfully converted {input_file}. Output saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error writing output file {output_file}: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert LibFuzzer programs to AFL++ compatible programs')
    parser.add_argument('-i', '--input_dir', required=True, help='Input directory containing LibFuzzer code files')
    parser.add_argument('-o', '--output_dir', help='Output directory for AFL++ code (default: <input_dir>_afl)')
    parser.add_argument('-e', '--extensions', default='.c,.cpp,.cc,.cxx', help='File extensions to process (comma-separated, default: .c,.cpp,.cc,.cxx)')
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist or is not a directory", file=sys.stderr)
        return 1
    
    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = f"{args.input_dir}_afl"
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception as e:
            print(f"Error creating output directory: {e}", file=sys.stderr)
            return 1
    
    # Get list of file extensions to process
    extensions = args.extensions.split(',')
    
    # Process all files with specified extensions in the input directory
    success_count = 0
    failure_count = 0
    
    for ext in extensions:
        pattern = os.path.join(args.input_dir, f"*{ext}")
        for input_file in glob.glob(pattern):
            if process_file(input_file, output_dir):
                success_count += 1
            else:
                failure_count += 1
    
    # Print summary
    print(f"\nConversion complete: {success_count} files converted successfully, {failure_count} files failed")
    if success_count > 0:
        print(f"Output files saved to {output_dir}")
    
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())