getwd()
statesInfo <- read.csv('stateData.csv')
subset(statesInfo, state.region == 1)

statesInfo[statesInfo$state.region == 1,]

subset(statesInfo, illiteracy > 1.5)
