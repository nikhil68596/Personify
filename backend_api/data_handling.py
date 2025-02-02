#Input: Company, job name, user applications object
def application_exists(company, applicationsObj):
    #For each application in the applicationsObj
    for i in range(len(applicationsObj)):
        application = applicationsObj[i]
        #If the application contains the company and job name
        if application["company"] == company:
            #Return the index
            return i
    return -1

