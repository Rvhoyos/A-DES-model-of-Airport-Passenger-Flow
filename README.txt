╔═════════════════════════════════════════════════════════╗
║         SMITHS FALLS (Dynamic) Airport Simulator        ║
║                      Raul Hoyos-Jimenez                 ║
║             SYSC 4005 - DES & Modeling Project          ║
╚═════════════════════════════════════════════════════════╝

### Set Up
1. **Prepare the Environment:**
   - Open the project in an IDE (recommended: PyCharm).
   - Optionally, clear files in the `airport/data/` folder.

2. **Configure the Virtual Environment:**
   - Open your terminal or command line in the virtual environment.
   - Ensure the following packages are installed:
     ```
     pip install pandas numpy simpy
     ```

### Execution
3. **Run the Simulation:**
   - Locate and execute the main method in `airport/Simulation.py`.
     - The system will prompt you to enter simulation parameters.
     - Enter the simulation time in days.
   - Observe that the simulation generates log files in `airport/data/`.

4. **Parse the Logs:**
   - Run `airport/Parser/log_functions.py` to process the generated log files.
   - This will create a new CSV file in `airport/data/` summarizing the logs.

5. **Analyze the Data:**
   - Execute `airport/Parser/analyze_data.py`.
   - This parses the CSV files and provides a detailed analysis.
   - Outputs include sorted events by type and tables by passenger.

6. **Visualize the Data (Optional):**
   - Run `visualizer/visualizer.py` to generate histograms from the CSV files.
   - Save the plots manually by right-clicking on them if needed.

### Understanding Simulation Console and Other Outputs
The final reports provide insights into airport operations, showcasing details such as passenger flow, and service times.
Review these outputs to assess the efficiency and effectiveness of different simulation scenarios.
