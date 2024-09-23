export default function InputParametersForm ({commandParameters, inputValues, setInputValues }) {

  // Function to handle input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;

    // Update the inputValues state by creating a new object that includes the new value
    setInputValues({
      ...inputValues,
      [name]: value, // Update the specific parameter's value based on the name attribute
    });
  };

  console.log('inputValues: ', inputValues);

 
  return (
    <>
      <ul>
        {commandParameters !== null ? (
          Object.entries(commandParameters).map(([key, value], index) => (
            <li key={index}>
              Parameter {index + 1}: {key}
              <ul>
                <li>Type: {value.dtype}</li>
                <li>Description: {value.description}</li>
                <li>
                  <label htmlFor={`param-${index}`}>Enter value:</label>
                  <input
                    id={`param-${index}`}
                    type={value.dtype === 'number' ? 'number' : 'text'}  // Dynamic input type
                    placeholder={`Enter ${key}`}
                    name={key}  // Use the parameter name as the key
                    value={inputValues[key] || ''} // Bind the input value to the state
                    onChange={handleInputChange} // Attach the change handler
                  />
                </li>
              </ul>
            </li>
          ))
        ) : (
          <p>No parameters available</p>
        )}
      </ul>
    </>
  );

  };