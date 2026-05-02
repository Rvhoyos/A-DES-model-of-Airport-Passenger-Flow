
# SMITHS FALLS Airport Simulator                  
# SYSC DES & Modeling Project                     

### Set Up
1. **Prepare the Environment:**
   - Open the project in an IDE.
   - Optionally, clear files in the `src/airport/data/` folder.
   - This is where you will find all the .CSV outputs of the steps below

2. **Configure the Virtual Environment:**
   - Open your terminal or command line in the virtual environment.
   - Ensure the following packages are installed:
     ```
     pip install pandas numpy simpy matplotlib
     ```

### Execution
3. **Run the Simulation:**
   - Execute `python -m src.airport.simulation` from the project root.
     - The system will prompt you to enter simulation parameters.
     - Enter the simulation time in days and the passenger arrival rate in passengers per hour.
   - Observe that the simulation generates log files in `src/airport/data/`.

4. **Parse the Logs:**
   - Run `python -m src.airport.Parser.log_functions` to process the generated log files.
   - This will create two new sorted CSV files organizing the logs.
   - Outputs include sorted events by type and tables by passenger.

5. **Analyze the Data:**
   - Execute `python -m src.airport.Parser.analyze_data`.
   - This parses the CSV files and provides two new files with detailed analysis.
   - The analysis is saved in `src/airport/data/` as a CSV file.

6. **Visualize the Data (Optional):**
   - Run `python -m src.airport.visualizer.visualizer` to generate histograms from the CSV files.
   - Save the plots manually by right-clicking on them if needed.

### Understanding Simulation Console and Other Outputs
The final reports provide insights into airport operations, showcasing details such as passenger flow, and service times.
Review these outputs to assess the efficiency and effectiveness of different simulation scenarios.

