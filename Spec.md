### Business requirement ### 

Design a multiple testing agents wofklow as below: 

Using Langgraph to define 
# Trigger point from slack: 

From the slack channel when i call @Quality-Engineer-Bot check the JIRA board to perform testing for any ticket in review column 

# Node 1 (agent test desinger): 

- This agent help to integrate with JIRA via MCP config in order to read the SRS in JIRA ticket / Output will be the e2e test cases for automation test 

# Node 2 (agent test execution): 

- This agent help to execute the test cases which is located in the JIRA ticket using playwright cli (from microsoft) 

# Node 3 (agent test report): 

- This agent help to analyze the test report, update the report in the status and post test report to slack channel. 


### Slack App-Level Token
your-slack-app-token


### Slack Bot User OAuth Token: 
your-slack-bot-token


pip install slack-bolt langgraph langchain-openai