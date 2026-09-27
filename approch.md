I am building resturant order management ai agent system using LangGraph .  
i will explain you very clearly what i want and what is teh architecture .i will even explain you the node states and edges .in the end i will even you test cases on scenarios to simulate wether they test or not .
The rough plan is - There is user , when the code runs the user will give an order , the order will be taken as an input which i will type .This order should go to the llm and the order as of now should contain the dish and order quantity . let us limit the dishes to just 3 per user and quantity as required .
if the user input is unreleted to a food ordering the llm should not process it 
Once the 11m has order dish and quantuty it will send that to a node caLLED order_confirm
The rtask of this order conform is to look at the menu (i will tell ypu the menu later in this prompt).
The \n this node will decide one of 3 case
the order is available 
the order is partially available means quantuty is not suficient the order is not available at all (dish being not
t i the menu or 0 quantity avilable)
it will put this in the status of the state (I will tell u the exact content of the langraph state as well)
Once the 1lm recievedd this
if the status is confiormed (full available) it should call another node called cook. the staus is partail or not available it should again prompty the user to decide
the user can either place a new order or can cionform if he wants to go ahead with the3 partial order
This order reties will be limited to 3 attempts menaing if after 3 attempt the user is not saidfied the system will come the the END node
Now wahen the cook node is called there can be
2 casea
eithet eh
cook is done then the stasus will beREady
and if the cook faikls we can use a prov function)|gives 40 % chance of failure and 60 % chance of success
if the cook fails there should be 1 more attempt allowed for cook to suceed. if the cook fails even after these then the 11m should issue a aplogy to the user and come to END state
if the cpook suuceeds, the status will be READY and the next node will be called which is serve simialr to cook this also has 2 cases servre pass or serve fail this also has 2 retry attempt
if the serve fails 2 times then the 11m should issue a aplogy to the user and come to END state
serve suceeds the status should bceomc ocmplete the l1m should uissue a message to the user saying your oder is complete
if serve fails then cook should becalled one more time to retry
if serve fails then cook should becalled one more time to retruy.
Note that if cok has exhausted its retrey attempts then it should not cook again and 11m should issue an apology and come to end state
Now the state of lagragph
there should be a annotated message be 11m and user
there should be order details dish name as str
required quantuty as int
available quantity as int 
order_conform will write the available quantuty by reading the menu the 11m should get to know the order confrm status by reading the state if a dish is not avilabel in the mnu then orderconform should write 0 as avail quantuty
then there should be status
each node will update the status as specifed in the above rules then order retry attemps which are 3
cook retry attempts which are 2
serve retry attempts which are 2 each time a filure haappend and a node
is retrying it should diecreent the couner
if any retry counter becomes 0 it means it is over it means llm shoukd ubnderattnd whether it has to givea retry or issue apology by reading this counter
in the end there should be a final result wether the order was completed , or not.
now one more addition i want to make to this is about the payment , when order is succesfull and payent scenerios which i will need options in ideation from you 
