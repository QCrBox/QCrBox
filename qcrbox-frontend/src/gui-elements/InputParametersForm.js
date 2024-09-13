export default function InputParametersForm ({nameValue, durationValue, setNameValue, setDurationValue }) {

    // Handler for text input change
    function handleTextChange(e) {
      setNameValue(e.target.value);
    }
  
    // Handler for integer input change
    function handleIntChange(e) {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value)) {
        setDurationValue(value);
      }
    }
  
    return (
      <div>
        <div>
          <label>
            Name:
            <input 
              type="text" 
              value={nameValue} 
              onChange={handleTextChange} 
            />
          </label>
        </div>
        <div>
          <label>
            Duration:
            <input 
              type="number" 
              value={durationValue} 
              onChange={handleIntChange} 
            />
          </label>
        </div>
      </div>
    );
  };