OpenPortfo — Assessment 3 submission pack
Student: Mai Gia Phu (s3927049)

This folder is the Canvas zip layout from the Assessment 3 specification.

1. Solution architecture
   OpenPortfo_Solution_Architecture.docx
   OpenPortfo_Solution_Architecture.pdf

2. doc_images/
   Figures used in the solution architecture document (Figure 1–5).

3. code/
   Full project source. Size is under 5 MB (build folders such as node_modules
   and .next are omitted). GitHub copy of the same tree:
   https://github.com/maiphh/openportfo.git
   No AWS credentials, SMTP passwords, or API keys are stored here.
   Use backend/.env.example as a template; never commit a real .env.

4. deploy/
   CloudFormation templates, Elastic Beanstalk Procfile / .ebextensions,
   and the packaging / deploy scripts. Runnable .zip bundles are built locally
   with package-eb.ps1 and package-lambda.ps1 (see deploy/README.txt).
   Do not put AWS keys in these files.

5. data/
   Athena SQL used on S3 snapshot files (under 5 MB).

Live URL (Learner Lab, us-east-1, as of 13 September 2026):
http://openportfo-api-env.eba-yrwmppgu.us-east-1.elasticbeanstalk.com
