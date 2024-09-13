export default function InputParametersForm ({textValue, intValue, setTextValue, setIntValue }) {

    // Handler for text input change
    function handleTextChange(e) {
      setTextValue(e.target.value);
    }
  
    // Handler for integer input change
    function handleIntChange(e) {
      const value = parseInt(e.target.value, 10);
      if (!isNaN(value)) {
        setIntValue(value);
      }
    }
  
    return (
      <div>
        <div>
          <label>
            Text Input:
            <input 
              type="text" 
              value={textValue} 
              onChange={handleTextChange} 
            />
          </label>
        </div>
        <div>
          <label>
            Integer Input:
            <input 
              type="number" 
              value={intValue} 
              onChange={handleIntChange} 
            />
          </label>
        </div>
      </div>
    );
  };