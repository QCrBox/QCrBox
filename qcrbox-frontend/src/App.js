// import './App.css';
import { useState } from 'react';
import MyButton from './gui-elements/MyButton.js';
import InputParametersForm from './gui-elements/InputParametersForm.js';


export default function MyApp() {
  const [calcID, setcalcID] = useState(null);
  const [apps, setApps] = useState([]);
  const [commands, setCommands] = useState([]);
  const [calculations, setCalculations] = useState([]);
  const [calcInvokeInfo, setCalcInvokeInfo] = useState(null);
  const [taskStatusInfo, setTaskStatusInfo] = useState(null);

  const [nameValue, setNameValue] = useState('Max');
  const [durationValue, setDurationValue] = useState(10);

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

  function invokeCommand() {
    fetch('/commands/invoke/', {
      method: 'POST',
      body: JSON.stringify({
        "application_slug": "dummy_cli",
        "application_version": "0.1.0",
        "command_name": "greet_and_sleep",
        "arguments": {"name": nameValue, "duration": durationValue}
      }),
    })
    .then(response => response.json())
    .then(json => {
      console.log(json);
      setcalcID(json.payload.calculation_id);
      setCalcInvokeInfo(json);
    });
    console.log('calculation ID: ', calcID);
    console.log('calcInvokeInfo', calcInvokeInfo);
  }

  function checkTaskStatus() {
    console.log(`/calculations/${calcID}/`);

    fetch(`/calculations/${calcID}/`, {
      method: 'GET',
    })
    .then(response => response.json())
    .then(json => {
      console.log(json);
      setTaskStatusInfo(json);
    });
  }

  // async function runCommand() {
  //   // Call startTask and wait for it to complete
  //   await invokeCommand()
  //   .then(() => {
  //     // Code here will run after the task has completed
  //     window.console.log('Code to run after task completed');
  //   })
  // }

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

      <MyButton onClick={checkTaskStatus} buttonText='Check Calculation Status'/> 
      <br /> 
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
            </>
          )
         : (
          <p></p>
        )}
      </ul>
    </div>
  );
}


