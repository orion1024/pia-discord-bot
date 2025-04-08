# Description

This file contains coding instructions to create the project.

# Project objectives

This project aims to create a Discord bot that will :
1. Monitor a specific channel for messages containing links to specific websites, such as but not limited to : YouTube, Twitter, etc.
2. When such a link is detected, it will create a Discord thread from it (if it's not already in one)
3. Then fetch information on the link content. The content fetched will be depending on the website.
4. The content will then be summarized/categorized by an LLM (probably Claude, but not set in stone).
5. The summarized content will be sent to a Coda table, as well as to the original channel.

Project should be modular : use existing libraries and tools when available, and be easily extensible to support :
- new webstites for the source links
- new LLMs for the summarization
- new target for the summarized content

The following modules will be developed :
- "commons" module that defines shared utilities for other modules
- Discord primitives to handle source data fetching
- Summarization primitives that will use the source data to generate the summary
- Target primitives that will use the summary to generate the target content


The project will start with YouTube for source, Claude for the summarization, and Coda for the target.

# Coding instructions

## Outlines

The development will proceed in iterative steps, utilizing the AI coding assistant (Cody) to generate and refine code for each phase. The process for each step is as follows:

1. **Initiate Step:** I request the coding assistant to begin the specific step.
2. **Receive Suggestions:** Cody provides initial suggestions, including relevant libraries, tools, and code snippets. If necessary, Cody will consult external documentation to inform its recommendations.
3. **Review and Fine-Tune:** We collaboratively review Cody’s suggestions, discussing potential improvements or adjustments.
4. **Approve Implementation:** I approve the refined suggestions for implementation.
5. **Code Generation:** Cody generates the code based on the approved suggestions.
6. **Testing and Validation:** I test the generated code to ensure it meets the requirements. If issues arise, we iterate with Cody to resolve them.
7. **Documentation:** Document the implemented code and any decisions made during the step.

## Steps

The development process will follow these steps:

### **Step 1: Identify Suitable Library**
- **Objective:** Determine which Python modules are best suited for leveraging the various API
- **Actions:**
  - Analyze project objectives to select appropriate modules
  - Cody should request additional documentation if necessary to make informed recommendations.
- **Expected Outcome:** A list of recommended Python libraries with justifications.

### **Step 2: Set Up Project Structure**

- **Objective:** Create the foundational files and directories for the project.
- **Actions:**
  - Create the following structure. If a file or folder already exists, dont overwrite it.
    ```
    /Project-Root
    ├── pia-discord-bot.py
    ├── pia-discord-bot_config.json
    ├── Modules/
    ├── Libraries/
    ├── .gitignore
    └── README.md
    ```
- **Expected Outcome:** A well-organized project directory with initial files and version control set up.

### **Step 3: Initialize Configuration and Modules**

- **Objective:** Set up the main script and global module to handle configuration loading.
- **Actions:**
  - In `ExtractServices.ps1`, write code to load `config.json`.
  - In `Modules/ExtractServices_globals.psm1`, define global variables and functions as needed.
  - Create a function `Load-Config` in `ExtractServices_globals.psm1` to handle configuration loading.
- **Expected Outcome:** `ExtractServices.ps1` and `ExtractServices_globals.psm1` can successfully load and access configuration settings.

### **Step 4: Define Skeleton Functions**

- **Objective:** Outline the functions required to achieve project objectives using skeleton code.
- **Actions:**
  - In `ExtractServices.ps1` and relevant modules, define placeholder functions such as:
    - `Get-WordDocument`
    - `Parse-Sections`
    - `Extract-ServiceData`
    - `Save-ToTsv`
- **Expected Outcome:** A clear structure of functions with no implementation details yet.

### **Step 5: Add Input and Output Parameters**

- **Objective:** Enable specification of input and output file paths via command-line arguments.
- **Actions:**
  - Use `Param` blocks in `ExtractServices.ps1` to add parameters:
    - `-InputPath` for the input Word file.
    - `-OutputPath` for the output TSV file.
- **Expected Outcome:** `ExtractServices.ps1` accepts and processes input and output file paths as arguments.

### **Step 6: Implement Word File Loading and Parsing**

- **Objective:** Load the Word document and parse its chapters and subchapters to extract service names.
- **Actions:**
  - Implement `Get-WordDocument` using COM objects to interact with Word.
  - Implement `Parse-Sections` to navigate through chapters and subchapters. Chapters and subchapters can be identified by their styles, which are all named "Titre X" where X is a number.
    Example Structure:
        **Titre 1**: Service Category
        **Titre 2**: Service SubCategory
        **Titre 3**: Service Name
        **Subchapter content** : A table. Each row contains a property of the service.
    Sections that don't contain a table should be ignored.
  - Extract the service name, category and subcategory for each service and display them using `Out-GridView`.
- **Expected Outcome:** Ability to load and parse the Word document, displaying extracted service names in a readable format.

### **Step 7: Save Extracted Data to TSV File**

- **Objective:** Persist the extracted data into a tab-delimited file.
- **Actions:**
  - Implement `Save-ToTsv` using `Export-Csv` with the `-Delimiter` parameter set to tab (`\t`).
  - Ensure that each service is represented as a single row with appropriate columns.
- **Expected Outcome:** A correctly formatted TSV file containing all extracted services.

### **Step 8: Enhance Data Extraction with Detailed Information**

- **Objective:** Extract additional details from tables within each subchapter of the Word document.
- **Actions:**
  - Update `Extract-ServiceData` to locate and parse tables within subchapters using COM objects.
  - Extract specific details as per the provided table structure.
  - Integrate the detailed data into the existing data grid.
- **Expected Outcome:** Comprehensive data extraction including detailed attributes from tables, reflected accurately in the TSV output.

### **Step 9: Implement Error Handling and Validation**

- **Objective:** Ensure the robustness of the application by handling potential errors and validating data.
- **Actions:**
  - Add `try-catch` blocks around file operations and parsing functions.
  - Validate the presence and correctness of required chapters and tables in the Word document.
  - Implement logging using `Write-Log` functions or the `Transcript` feature to track errors and processing steps.
- **Expected Outcome:** The application gracefully handles errors and logs relevant information for troubleshooting.

### **Step 10: Write Unit Tests**

- **Objective:** Ensure code reliability through automated testing.
- **Actions:**
  - In the `Tests/` directory, write unit tests for each major function using the **Pester** framework.
  - Test scenarios include successful data extraction, handling missing chapters, and invalid input files.
- **Expected Outcome:** A suite of tests that validate the functionality and robustness of the codebase.

### **Step 11: Documentation and Usage Instructions**

- **Objective:** Provide clear documentation for future maintenance and user guidance.
- **Actions:**
  - Update `README.md` with project description, setup instructions, usage examples, and contribution guidelines.
  - Comment the script and module files thoroughly to explain complex logic and decisions.
- **Expected Outcome:** Comprehensive documentation that facilitates easy understanding and usage of the project.


## Coding Standards

- Follow PEP8 Standards: Adhere to the widely accepted PEP8 style guide for naming conventions, indentation, line length, spacing, and more to improve code readability and maintain consistency.
- Write Clean, Modular Code: Structure your code in functions, classes, and modules so that each component has a single responsibility and can be reused and tested independently.
- Include Comprehensive Comments: Comment your code effectively to explain the purpose of functions, complex logic, and overall code flow without cluttering the source code.
- Emphasize Readability: Use descriptive variable and function names, and maintain clear logical structures to enhance maintainability and ease of understanding for others.
- Implement Robust Error Handling: Use try-except blocks where appropriate to catch exceptions, and provide meaningful error messages to facilitate debugging and maintenance.
- Utilize Python’s Standard Library: Prefer built-in libraries over external dependencies when feasible, and clearly document when and why external libraries are used.
- Follow Best Practices for Testing: Integrate unit tests using frameworks like unittest or pytest to validate the functionality of your code and support continuous integration.
- Document API and Usage: Write clear docstrings for functions, classes, and modules that describe their input parameters, return types, and potential exceptions.
- Ensure Compatibility Across Environments: Write code that is compatible with multiple Python versions if needed, and use virtual environments or dependency managers (e.g., pipenv, Poetry) to handle packages.
- Optimize Code Performance: Consider algorithm complexity and resource management; use profiling tools to identify bottlenecks, and refactor code where necessary for improved performance.
- Leverage Modern Python Features: Utilize recent Python enhancements (such as type hints, f-strings, and context managers) where appropriate to write cleaner, more expressive code.
- Handle Edge Cases: Think through and code for possible edge cases and input anomalies to ensure that your software behaves predictably under all scenarios.
- Maintain Security Best Practices: Sanitize inputs when interacting with external data sources, and be cautious with the handling of sensitive information.
- Use Version Control: Integrate with version control systems (e.g., Git) to track changes, manage branches, and facilitate collaborative development.
- Provide Clear Documentation: Generate and maintain user-facing and developer-facing documentation, and consider using tools such as Sphinx for creating robust documentation from docstrings.