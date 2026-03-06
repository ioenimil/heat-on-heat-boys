from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import AppRunner, ECR
from diagrams.aws.database import RDS
from diagrams.aws.storage import S3
from diagrams.aws.management import Cloudwatch
from diagrams.aws.general import Client, User
from diagrams.onprem.workflow import Airflow
from diagrams.onprem.vcs import Github
from diagrams.onprem.ci import GithubActions

GRAPH_ATTR = {
    "splines": "ortho",
    "nodesep": "0.8",
    "ranksep": "1.2",
    "fontname": "Sans-Serif",
    "fontsize": "16",
    "bgcolor": "white",
    "compound": "true",
}

with Diagram("ServiceHub Production Architecture", show=False, graph_attr=GRAPH_ATTR, direction="LR", filename="servicehub_architecture"):

    with Cluster("External Triggers", graph_attr={"bgcolor": "#E5F5E0"}):
        end_user = User("End Users\n(Browser accessing Thymeleaf)")
        dev_team = Client("Dev Team\n(Backend/DevOps/Data)")

    with Cluster("CI/CD (Source to Image)", graph_attr={"bgcolor": "#E3F2FD"}):
        gh_repo = Github("GitHub Repo\n(Source Code)")
        gh_actions = GithubActions("GitHub Actions\n(Build Java & Docker)")

    with Cluster("AWS Cloud (Production Account)", graph_attr={"bgcolor": "#fafafa", "pencolor": "#f57c00"}):
        ecr = ECR("Amazon ECR\n(Container Registry)")
        cw_logs = Cloudwatch("CloudWatch\n(Logs & Traces)")
        mwaa_s3 = S3("S3 Bucket\n(Airflow DAGs & Logs)")
        
        app_runner = AppRunner("AWS App Runner\n(Java/Thymeleaf Service)")

        with Cluster("VPC (Virtual Private Cloud)"):
            with Cluster("Private Subnets (Data Tier)", graph_attr={"bgcolor": "#fff3e0"}):
                rds_db = RDS("Amazon RDS\n(PostgreSQL 16)")
                mwaa_env = Airflow("Amazon MWAA\n(Data Engineering)")

    dev_team >> Edge(label="Git Push") >> gh_repo
    gh_repo >> Edge(label="Triggers Workflow") >> gh_actions
    gh_actions >> Edge(label="Pushes Docker Image", color="#0277BD") >> ecr
    
    ecr >> Edge(style="dashed", label="Auto-Deploy Trigger", color="#0277BD") >> app_runner

    end_user >> Edge(label="HTTPS (443)", color="#2E7D32", penwidth="2.0") >> app_runner
    app_runner >> Edge(label="SQL (5432)\nvia VPC Connector", color="#D84315", penwidth="2.0") >> rds_db
    app_runner >> Edge(style="dotted", label="Logs/Traces") >> cw_logs

    mwaa_env >> Edge(label="ETL Read/Write", color="#D84315") >> rds_db
    mwaa_env - Edge(style="dotted") - mwaa_s3
    mwaa_env >> Edge(style="dotted", label="Logs") >> cw_logs

print("Diagram generated successfully as servicehub_architecture.png")