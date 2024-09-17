// import './App.css';
import { useState } from 'react';
import MyButton from './gui-elements/MyButton.js';
import InputParametersForm from './gui-elements/InputParametersForm.js';


export default function MyApp() {
  // const [calcID, setcalcID] = useState(null);
  const [apps, setApps] = useState([]);
  const [commands, setCommands] = useState([]);
  const [calculations, setCalculations] = useState([]);
  const [calcInvokeInfo, setCalcInvokeInfo] = useState(null);
  const [taskStatusInfo, setTaskStatusInfo] = useState(null);

  const [nameValue, setNameValue] = useState('Max');
  const [durationValue, setDurationValue] = useState(10);

  const [calcDuration, setCalcDuration] = useState(null);

  async function listApplications() {

    await fetch('/applications/', {
      method: 'GET',
    })
    .then(response => response.json())
    .then(json => {
      console.log(json);
      setApps(json);
    });
  }

  function listCommands() {
    fetch('/commands/', {
      method: 'GET',
    })
      .then(response => response.json())
      .then(json => {
        console.log(json);
        setCommands(json);
      });
  }

  function listCalculations() {
    fetch('/calculations/', {
      method: 'GET',
    })
      .then(response => response.json())
      .then(json => {
        console.log(json);
        setCalculations(json);
      });
  }

  let startTime;
  let endTime;
  let duration;

  async function invokeCommand() {

    // Record the start time
    startTime = Date.now();
    console.log('start time: ', startTime);

    const response = await fetch('/commands/invoke/', {
      method: 'POST',
      body: JSON.stringify({
        "application_slug": "dummy_cli",
        "application_version": "0.1.0",
        "command_name": "greet_and_sleep",
        "arguments": {"name": nameValue, "duration": durationValue}
      }),
    })

    const data = await response.json();
    console.log(data);
    setCalcInvokeInfo(data);
    const taskId = await data.payload.calculation_id;
    console.log(data.payload.calculation_id);

    // Wait for the task to complete
    const result = await checkTaskStatus(taskId);
    console.log(result);

    // Record the end time
    endTime = Date.now();
    console.log('end time: ', endTime);

    // Calculate the duration in seconds
    duration = (endTime - startTime) / 1000;
    console.log(`Task completed in ${duration} seconds`);
    setCalcDuration(duration);
  }

  async function checkTaskStatus(taskId) {

    console.log(`/calculations/${taskId}/`);

    return new Promise(async (resolve, reject) => {
      const poll = async () => {
        
        try {
          const response = await fetch(`/calculations/${taskId}/`, {
              method: 'GET',
            });
            const data = await response.json();
            setTaskStatusInfo(data);

            if (data.status === 'successful') {
              resolve(data.result); // Task completed, resolve the promise with the result
              console.log(data);
            } else if (data.status === 'error') {
              reject(new Error(data.error)); // Task failed, reject the promise
              alert('Error: ', data.error); // Send an alert to the user
            } else {
              window.console.log('Task not yet completed, checking again...');
              setTimeout(poll, 1000); // Poll every 5 seconds
              
              // Record the end time
              endTime = Date.now();
              console.log('end time: ', endTime);

              // Calculate the duration in seconds
              duration = (endTime - startTime) / 1000;
              console.log('duration: ', duration);
              setCalcDuration(duration);
            }
          } catch (error) {
            reject(error); // Handle fetch errors
            alert('Error: ', error);
          }
        };
        poll();
      });
  }


  return (
    <div>
      <h1 className='App'>QCrBox Examples</h1>

      <MyButton onClick={listApplications} buttonText='List Applications'/>
      <br />
      <ul>
        {apps.length > 0 ? (
          apps.map(app => (
            <li key={app.id}>
              {app.name}
            </li>
          ))
        ) : (
          <p></p>
        )}
      </ul>
      
      <MyButton onClick={listCommands} buttonText='List Commands'/>      
      <br /> 
      <ul>
        {commands.length > 0 ? (
          commands.map(command => (
            <li key={command.id}>
              {command.name}
            </li>
          ))
        ) : (
          <p></p>
        )}
      </ul>

      <MyButton onClick={listCalculations} buttonText='List Calculations'/>    
      <br /> 
      <ul>
        {calculations.length > 0 ? (
          calculations.map(calculation => (
            <li key={calculation.calculation_id}>
              {calculation.calculation_id}
            </li>
          ))
        ) : (
          <p></p>
        )}
      </ul>

      <InputParametersForm 
        nameValue={nameValue} 
        durationValue={durationValue} 
        setNameValue={setNameValue} 
        setDurationValue={setDurationValue} 
      />

      <MyButton onClick={invokeCommand} buttonText='Invoke Greet and Sleep Command'/>    
      <br /> 
      <p>Calculation Invocation Information:</p>
      <ul>
        {calcInvokeInfo !== null ? (
            <>
              <li>
                Msg: {calcInvokeInfo.msg}
              </li>
              <li>
                Status: {calcInvokeInfo.status}
              </li>
              <li>
                Calculation ID: {calcInvokeInfo.payload.calculation_id}
              </li>
            </>
          )
         : (
          <p></p>
        )}
      </ul>

      {/* <MyButton onClick={checkTaskStatus} buttonText='Check Calculation Status'/>  */}
      <br /> 
      <p>Calculation Status:</p>
      <ul>
        {taskStatusInfo !== null ? (
            <>
              <li>
                Calculation ID: {taskStatusInfo.calculation_id}
              </li>
              <li>
                Status: {taskStatusInfo.status}
              </li>
              <li>
                Stdout: {taskStatusInfo.stdout}
              </li>
              <li>
                Calculation duration: {calcDuration}
              </li>
            </>
          )
         : (
          <p></p>
        )}
      </ul>
    </div>
  );
}


