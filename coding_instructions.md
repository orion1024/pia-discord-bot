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

## Modularity specifics

The following modules will be developed :
- "commons" module that defines shared utilities for other modules
- Discord primitives to handle link detection
- Content primitives to fetch raw source data
- Summarization primitives that will use the source data to generate the summary
- Target primitives that will use the summary to generate the target content

The intended modularity can be achieved by using standard methods for high-level data handling, which take as one of their parameter a function to handle low-level data handling.
For instance, the module to fetch the raw data could use a high-level function which :
1. fetch the raw data using the passed function. The function will be different for each website.
2. parse the raw data in a common format (defined in the commons module), independent of the website, which will allow the next modules to handle it seemlessly.
Apply this principle to all modules.

The project will start with YouTube for source, Claude for the summarization, and Coda for the target.

All strings that are used to post content on Discord or Coda will be stored in a single file named "strings.py".
Methods specific to a platform should be stored in a specific file named after the platform.

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
- **Objective:** Set up project configuration and prepare modular code frameworks.
- **Actions:**
  - Create or update the `pia-discord-bot_config.json` file with necessary API keys, tokens, and default settings.
  - Initialize the `Modules/` directory by creating subdirectories (with `__init__.py` files) for each module (e.g., Discord, Summarization, Target, Commons).
  - Implement a configuration loader function that reads and validates the configuration file.
- **Expected Outcome:** The bot’s configuration settings are loaded correctly, and the modules are primed for further development.

### **Step 4: Define Skeleton Functions**
- **Objective:** Outline the core functions for each module to create a blueprint for future development.
- **Actions:**
  - Create placeholder (stub) functions within each module that detail expected inputs, outputs, and overall purpose.
  - Document each function with clear docstrings that describe parameters, expected return values, and potential exceptions.
- **Expected Outcome:** A clear blueprint with defined function names, arguments, and documentation, providing a roadmap for subsequent coding.

### **Step 5: Implement Discord Bot Connection and Message Monitoring**
- **Objective:** Establish connection to the Discord API and begin monitoring messages on designated channels.
- **Actions:**
  - Assist me in obtaining the prerequisites for the bot (Discord API token, etc.)
  - Set up the bot’s authentication and connection logic.
  - Implement event listeners to monitor messages and log activities.
- **Expected Outcome:** The Discord bot connects successfully to the server and monitors/logs incoming messages.

### **Step 6: Create Link Detection and Thread Creation Logic**
- **Objective:** Detect messages containing supported website links and generate corresponding threads.
- **Actions:**
  - Develop a parser to scan messages for URLs (specifically targeting sites like YouTube, Twitter, etc.).
  - Implement a function to automatically create a new Discord thread for a given link if needed. If an existing thread is found, the bot should not create a new one, and use the existing one instead.
  - Set up an easy way for all modules to write a message to the Discord thread.
- **Expected Outcome:** When a message with a supported link is detected, the bot creates a thread (unless one already exists).

### **Step 7: Implement Content Fetching Module**
- **Objective:** Retrieve content from the source websites corresponding to the detected links.
- **Actions:**
  - Write functions that interface with website APIs or use reliable scraping methods (starting with YouTube).
  - Ensure proper error handling and fallback procedures if the content cannot be fetched.
- **Expected Outcome:** Content is fetched and prepared for processing (such as summarization), with robust error handling.

### **Step 8: Integrate Summarization Module with LLM**
- **Objective:** Generate summaries using a large language model (LLM), such as Claude, based on the fetched content.
- **Actions:**
  - Develop an interface for sending content to the summarization API.
  - Handle responses from the LLM, ensuring proper formatting and clarity.
  - Maintain flexibility for future integration with other LLMs if needed.
- **Expected Outcome:** The LLM produces reliable summaries of the fetched content, which are then ready for subsequent processing.

### **Step 9.1: Add a local cache to store summary items **
- **Objective:** Maintain a local JSON file containing the summary item collection
- **Actions:**
  - Use the local file to detect duplicates
  - After a summary item has been generated, add it to the local file.  
- **Expected Outcome:** Up-to-date list of summaries are stored in local file

### **Step 9.2: Develop Full Target Module for Content Delivery**
- **Objective:** Deliver the summarized content to the chosen endpoints, such as a Coda table and the original Discord channel.
- **Actions:**
  - Create functions that interact with the Coda API to update a table with the summary.
  - Ensure that the original Discord channel receives a well-formatted message containing the summary.
  - Implement error handling and retries for network or API issues.
- **Expected Outcome:** Summaries are successfully posted to the designated Coda table and the original Discord channel.

### **Step 10 : Add duplicate detection**
- **Objective:** Use the code table to fetch existing threads and summaries to detect duplicates.
- **Actions:**
  - Set up a function to fetch the code table and extract existing threads and summaries.
  - Use it in the Discord monitoring function to detect duplicates.
  - If duplicates are detected, the bot should create a new thread with a link to the existing thread, with a message explaining the duplicate.
- **Expected Outcome:** Summaries are successfully posted to the designated Coda table and the original Discord channel.


### **Step 11: Integrate and Test End-to-End Workflows**
- **Objective:** Ensure seamless integration between all individual modules.
- **Actions:**
  - Build integration tests or conduct manual end-to-end tests to simulate the complete process—from link detection to updating the target with a summary.
  - Identify and resolve any issues or bottlenecks in the data flow.
- **Expected Outcome:** A smooth, error-free end-to-end process where messages are detected, threads created, content fetched, summarized, and delivered reliably.

### **Step 12: Write Unit Tests**
- **Objective:** Develop comprehensive tests for individual functions and modules to ensure code reliability.
- **Actions:**
  - Use testing frameworks like `unittest` or `pytest` to write tests.
  - Cover key functionalities in Discord connection, link detection, content fetching, summarization, and target delivery modules.
  - Set up continuous integration (CI) to run tests automatically.
- **Expected Outcome:** A robust suite of unit tests that ensures any future changes do not break existing functionality.

### **Step 13: Documentation and Usage Instructions**
- **Objective:** Create detailed documentation for both developers and end users.
- **Actions:**
  - Generate comprehensive README files for project setup, installation, and contribution guidelines.
  - Document each API function and module thoroughly with inline docstrings and external documentation using tools like Sphinx.
  - Provide usage examples, troubleshooting tips, and contact details for support.
- **Expected Outcome:** Clear and accessible documentation that facilitates onboarding and ongoing development.

# Coding Standards

- **Follow PEP8 Standards:** Adhere to naming conventions, indentation, spacing, and other guidelines to improve code readability.
- **Write Clean, Modular Code:** Organize code into functions, classes, and modules to ensure each component has a single responsibility.
- **Include Comprehensive Comments:** Provide clear comments explaining the purpose of functions, complex logic, and overall code flow.
- **Emphasize Readability:** Use descriptive names and maintain clear logical structures for ease of future maintenance.
- **Implement Robust Error Handling:** Use try-except blocks with meaningful error messages to facilitate troubleshooting.
- **Utilize Python’s Standard Library:** Prefer built-in libraries where possible, and document any external dependencies.
- **Follow Best Practices for Testing:** Incorporate unit tests using frameworks like `unittest` or `pytest` and support continuous integration.
- **Document API and Usage:** Write detailed docstrings for functions, classes, and modules outlining parameters, return types, and exceptions.
- **Ensure Compatibility Across Environments:** Write code that supports multiple Python versions and use virtual environments or dependency managers (e.g., pipenv, Poetry) as needed.
- **Optimize Code Performance:** Consider algorithm complexity and use profiling tools to identify and resolve bottlenecks.
- **Leverage Modern Python Features:** Utilize type hints, f-strings, and context managers for cleaner, more expressive code.
- **Handle Edge Cases:** Anticipate and code for potential edge cases to ensure predictable behavior.
- **Maintain Security Best Practices:** Sanitize external inputs and handle sensitive data with caution.
- **Use Version Control:** Track changes using systems like Git and facilitate collaborative development.
- **Provide Clear Documentation:** Maintain both user-facing and developer-facing documentation, using tools like Sphinx if possible.

TODO :
- add keywords to the summaries, to facilitate later semantic search.
  - name of the people involved in the content should be included by default
- add commands, for instance :
  - in a thread
    - trigger a new evaluation of a link (cooldown ?)
    - post in the thread related similar content (do it by default ?)
  - outside a thread
    - list categories of content
    - post list of content regarding a certain category)
