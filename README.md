# eBay Automation Workflow

This project automates eBay product listing and inventory management. The full codebase and documentation will be developed here.

## Project Structure
- └── : Holds input CSVs and the local SQLite database.
- └── : Contains all the Python source code.
  - └── : Handles communication with external APIs (eBay, Google).
  - └── : The main application logic and orchestration.
  - └── : Helper functions and utilities.
- └── : Standalone scripts for tasks like database migration.
- └── : HTML templates for the web dashboard.
- └── : Unit and integration tests.
- └── : Configuration settings (API keys, file paths).
- └── : The main entry point to run the application.

## How to Upload Files to this Repository

1.  **Install the GitHub CLI:** If you don\'t have it, install it from [cli.github.com](https://cli.github.com/).
2.  **Clone the repository:** Open a terminal and run the following command:
    ```bash
    gh repo clone Cbello11/ebay-automation-workflow
    ```
3.  **Add your files:** Copy the files you want to upload into the correct directory within the cloned folder. For example, your product data CSV should go into the  directory.
4.  **Commit and push the changes:** In your terminal, navigate into the repository folder () and run these commands:
    ```bash
    # Add all new and modified files to the staging area
    git add .

    # Commit the changes with a descriptive message
    git commit -m "Add my product data file"

    # Push the changes to the GitHub repository
    git push
    ```

