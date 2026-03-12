#define PinA 2  
#define PinB 3  

unsigned long time = 0; 
long count = 0; 
long num = 0;


void setup()
{
  Serial.begin(9600);

  pinMode(PinA,INPUT); 
  pinMode(PinB,INPUT); 

  attachInterrupt(0, blinkA, LOW);  
  attachInterrupt(1, blinkB, LOW);  

  time = millis(); 
}

void loop()
{
  while (num != count)
  {
    num = count;
    Serial.println(num);
  }
}

void blinkA()
{
  if ((millis() - time) > 3)
        count ++; 
  time = millis();
}

void blinkB()
{
  if ((millis() - time) > 3)  
        count --;
  time = millis();
}
