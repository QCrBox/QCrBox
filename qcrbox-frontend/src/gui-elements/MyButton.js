
export default function MyButton({ onClick, buttonText }) {
  return (
    <button onClick={onClick}>
      {buttonText}
    </button>
  );
}