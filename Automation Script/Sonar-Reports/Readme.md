# Sonarqube must be installed and running along with jenkins on the same server.

# The parameters-pipeline is used for the setup.

# The following parameters needs to be setup 

    1. (String Parameter)   SONAR_HOST = //url
    2. (Choice Parameter)   SONAR_PROJECT = values   //name of projects
    3. (String Parameter)   REPORT_NAME = sonarqube_report.html
    4. (String Parameter)   CHARTS_DIR = charts
    5. (Password Parameter) SONAR_TOKEN = token-id  // from the sonarqube-dashboard


# Pipeline will use Pipeline script

# Refer Jenkinsfile for the Pipeline script 