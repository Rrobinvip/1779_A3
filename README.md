# ECE 1779 A3 Pic cache and recognition - Group 17

## To run
Script must be executed with current shell with intergrated mode. In most cases, Ubuntu use BASH, and macOS use ZSH.
`<shell> -i start.sh`

To find out your shell with `echo $SHELL`.

## To create environment:
1. Create the environment from the `environment.yml` with `conda env create -f environment.yml`
1. Activate the new environment with `conda activate <name_env>`, in this case, the `<name_env>` is `MEMCACHE`
3. Inspect packages with `conda list`

## General requirements
Your application implementation should comply with the following requirements:

1. Storage: All persisted data should be stored on DynamoDB and S3. Use each one of them appropriately.
2. Lambda: You should use Lambda functions to develop and deploy your application.
3. Background Process: In addition to the main web application functionality, i.e., serving client requests, your application should also include a separate process (implemented as AWS Lambda function(s)) that runs in the background and does something useful for your web application (for example, doing some analytics on collected data, reacting to events, garbage collection, or something else).
4. Deployment: You may use Zappa or similar tools to deploy your application, but you must not use Zappa to deploy the background process, rather you should work directly with Lambda functions.
5. Performance Results: Run convincing performance experiments that track latency and throughput as one important control variable of your web application changes. You are free to choose which variable it is and how it changes as long as it is a relevant choice within the context of your web application. For example, you could show requests per unit of time, or number of functions spawned in order to handle concurrent requests, or something else of this nature that best demonstrates the performance of your application. 
6. Cost Model: You should create a model for the total AWS costs incurred by deploying your application on AWS. Take all the AWS services you use (Lambda, API Gateway, S3, Network bandwidth, etc.) into account and predict the long-term deployment cost of your application based on the following parameters:
7. Average number of users per month that will be using your application,
8. Average number of invocations per month.
9. For this project you can use as many AWS services as you want. AWS has many services (such as image recognition, speech detection, geographical services, etc.) that your application could benefit from. Feel free to use them. The idea is to show modern applications can be built quickly by connecting already available services.

