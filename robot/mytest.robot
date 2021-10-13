*** Settings ***
Library             Collections
Library             String
Library             BuiltIn
Library             SSHLibrary
Library             Process
Library             OperatingSystem

*** Variables ***

*** Keywords ***
Create random 0 or 1
    ${Random Numbers}=     generate random string  1  01
    [Return]  ${Random Numbers}

*** Test Cases ***
Execute Command And Verify Output
    [Tags]              mytest1
    ${number}=  Create random 0 or 1
    #${int_number}=  convert to integer  ${number}
    should be equal as strings  1   ${number}[0]








