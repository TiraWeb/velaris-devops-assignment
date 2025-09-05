# Velaris DevOps Assignment - Report  

This report goes over how I set up the Velaris DevOps environment, the steps I followed, and why I made certain choices along the way.  



## 1. How I Set Up the Environment  

I took a code-first approach: built the app, containerized it, and then used Terraform to set up the cloud infrastructure.  

### Step 1: Project Structure  
The project is split into two main folders:  
- `/src` → application code  
- `/terraform` → infrastructure code  

### Step 2: Application Development  
- **Web App:** A small Flask app in Python that serves a homepage showing health check results from DynamoDB.  
- **Validation Script (Lambda):**  
  - Gets current time from `timeapi.io`  
  - Compares it with container UTC time  
  - Checks the app endpoint health  
  - Saves result (OK or FAILED) to DynamoDB  
  - Sends SNS alert if a check fails  
- **Business Hours Script (Lambda):** Starts/stops ECS service by adjusting the task count at specific times.  

### Step 3: Containerization  
A `Dockerfile` packages the Flask app with its dependencies. A slim Python image keeps the container lightweight.  

### Step 4: Infrastructure as Code (Terraform)  
Terraform defines all AWS resources, including:  
- Networking (VPC, Subnets, Security Groups)  
- ECR repository  
- ECS Fargate cluster + service  
- Application Load Balancer  
- DynamoDB table  
- IAM roles & policies (least privilege)  
- Lambda functions + EventBridge rules  
- SNS topic for alerts  
- CloudWatch dashboard  

This makes the setup fully automated and repeatable.  



## 2. Provisioning and Tearing Down

### Prerequisites  
- AWS CLI installed & configured  
- Terraform installed  
- Docker installed & running  

### Steps to Provision  
1. **Set Alert Email:** Update `terraform/variables.tf` with your email.  
2. **Build Lambda Packages:** Run the packaging commands from the project root.  
3. **Deploy with Terraform:**  
   ```bash
   cd terraform
   terraform init
   terraform apply -auto-approve
   Copy alb_dns_name and ecr_repository_url from the output
4. **Deploy App Container**
   #### Login to ECR
     ```bash
     aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <your_ecr_repository_url>
    ```
     
   #### Build, tag, and push image
   ```bash
     docker build -t velaris-app .
     docker tag velaris-app:latest <your_ecr_repository_url>:latest
     docker push <your_ecr_repository_url>:latest
   
5. **Start ECS Service**
   ```bash
     aws ecs update-service --cluster velaris-cluster \
       --service velaris-service \
       --force-new-deployment \
       --region ap-south-1
6. **Final Steps**
   - Confirm the SNS subscription (check your email)
   - Open the app in a browser using the 'alb_dns_name'

### Tearing Down
```bash
terraform destroy -auto-approve
```


## 3. Running the scripts
- Automated:
  - Validation script runs every 5 mins (via EventBridge)
  - Business hours script runs at 9 AM UTC (start) and 6 PM UTC (stop)
- Manual Testing:
  - Go to AWS Console → Lambda → velaris-time-checker
  - Use the Test tab to trigger it manually



## 4. Assumptions & Design Choices

### Assumptions
  - "Validate Correctness": This was interpreted as a need to verify that the container's system clock is not significantly drifted from a trusted external time source. The implementation checks if the hour of      the container's clock matches the hour from the time API. A mismatch triggers a "FAILED" status and an alert
  - Public repo = no secrets hardcoded (all configs use environment variables)

### Design Choices
  - Serverless-First Architecture (Fargate, Lambda, DynamoDB):
    Reasoning: This approach was chosen to build a modern, cost-effective, and low-maintenance solution. Fargate eliminates the need to manage EC2 instances. Lambda is the most efficient way to run periodic         code without paying for an idle server. DynamoDB provides a fully managed, scalable database that perfectly fits our simple key-value data model, avoiding the cost and complexity of a relational RDS database
  - Infrastructure as Code (Terraform):
    Reasoning: Using Terraform allows the entire cloud environment—from networking to application services—to be defined as code. This makes the setup fully repeatable, auditable, and easy to create and destroy     on demand, which is a core tenet of modern DevOps and CI/CD practices
  - Decoupled Monitoring Logic:
    Reasoning: The health check logic resides in a separate Lambda function, not inside the application container. This is a critical design choice for resilience. It allows the monitoring system to function        and send alerts even if the main application has crashed or is completely unresponsive


