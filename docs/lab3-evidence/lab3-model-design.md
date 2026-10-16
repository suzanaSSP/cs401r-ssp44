# Design Report - Lab 3

## Model I'll be using
**Track C: ReAct Agents**

## Section 1: Churn Model
#### Why gradient boosting rather than logistic regression or a neural network, for this dataset, ~10,000 customers, 13 tabular features, an interpretability requirement from the retention team? What would have to change for you to switch?

If I were to use Logistic Regression, I would assume that churn has a linear relationship with my data. However, churn can have a relationship with many features from my data. 
In addition, this data is too small to use a neural network. It would require tunning and would be too complex. That is why gradient boosting is the best alternative, it doesn't only work with linear relationships and is not as complex as a neural network. 
I would switch to logistic regression, if the retention team needed it to be extremely simple to audit or maintain, or if it needed coefficient-level explanations. I would switch to neural networks if the dataset became much larger or included high dimensional inputs, like images, or clickstream sequences. 


## Section 2: What your features bought you

#### Report the recency-only baseline against your full model. If the lift was small, say so and explain why. Which features carried real signal, and which were decorative?

|Metric                             |	    Your value	       |Threshold       |
|---------                          |-------------------------|----------------|
|AUC-ROC (test set)	                |   0.7764                |report it — no fixed threshold|
|Precision @ top 10%                |	0.6900       |≥ 0.50
|Recall @ top 10%                   |	     0.3136  |≥ 0.25
|AUC lift over recency-only baseline|[0.0331, 0.0731]|95% CI must exclude zero

## Section 3: LLM system
#### Why RAG over fine-tuning (Track B), or an agent over a simpler pipeline (Track C)? Name the primary production risk of your choice.

I'm choosing to do Track C and build react agents. In this case, a ReAct Agent is preferred over a simple pipeline because it's going to be dealing with customer support where each task is going to be different. Each customer is going to have different needs, so the agent will need to call different tools to get correct information. A fixed pipeline would not be able to do that. That is why an agent that thinks, reasons, and acts according to the customer needs is needed. 

## Section 4: Alternative
#### What you would do differently with 10× the time or data.